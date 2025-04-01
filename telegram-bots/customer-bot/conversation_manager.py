"""
Conversation Manager - Context management and smart features
Task 5.4: Context management (Redis, last 5 messages, cart, follow-ups)
Task 5.5: Smart features (same as last time, usual order, modifications)
Task 5.6.2: Conversation state machine
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Allow importing redis_client from agent-service
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root / "agent-service"))

try:
    from redis_client import get_sync_client as _get_redis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Conversation states (5.6.2 state machine)
STATE_BROWSING = "browsing"
STATE_ORDERING = "ordering"
STATE_AWAITING_CLARIFICATION = "awaiting_clarification"
STATE_CONFIRMING = "confirming"
STATE_CONFIRMED = "confirmed"

CONTEXT_TTL_SECONDS = 3600  # 1 hour

# Cache whether Redis is reachable (avoid repeated failed connection attempts)
_redis_reachable: bool | None = None


def _check_redis_reachable() -> bool:
    """Check once if Redis is reachable; cache the result."""
    global _redis_reachable
    if _redis_reachable is not None:
        return _redis_reachable
    if not _REDIS_AVAILABLE:
        _redis_reachable = False
        return False
    try:
        import redis as _redis_lib
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = _redis_lib.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True)
        client.ping()
        _redis_reachable = True
    except Exception:
        _redis_reachable = False
    return _redis_reachable


class ConversationManager:
    """
    Manages per-user conversation context stored in Redis.
    Falls back to in-memory dict if Redis is unavailable.
    """

    def __init__(self):
        self._memory: dict[str, dict] = {}  # fallback in-memory store

    def _redis(self):
        if not _check_redis_reachable():
            return None
        if _REDIS_AVAILABLE:
            try:
                return _get_redis()
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # 5.4.1 Store conversation context in Redis
    # ------------------------------------------------------------------

    def _context_key(self, user_id: int | str) -> str:
        return f"conversation:{user_id}"

    def get_context(self, user_id: int | str) -> dict:
        """Load conversation context for a user."""
        key = self._context_key(user_id)
        redis = self._redis()
        if redis:
            try:
                raw = redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.warning("get_context Redis error: %s", exc)

        # Fallback to memory
        return self._memory.get(key, self._empty_context())

    def save_context(self, user_id: int | str, context: dict) -> None:
        """Persist conversation context."""
        key = self._context_key(user_id)
        context["updated_at"] = datetime.now(timezone.utc).isoformat()

        redis = self._redis()
        if redis:
            try:
                redis.setex(key, CONTEXT_TTL_SECONDS, json.dumps(context))
                return
            except Exception as exc:
                logger.warning("save_context Redis error: %s", exc)

        self._memory[key] = context

    def clear_context(self, user_id: int | str) -> None:
        """Clear conversation context (e.g., after order placed)."""
        key = self._context_key(user_id)
        redis = self._redis()
        if redis:
            try:
                redis.delete(key)
            except Exception:
                pass
        self._memory.pop(key, None)

    @staticmethod
    def _empty_context() -> dict:
        return {
            "last_messages": [],   # 5.4.2 last 5 messages
            "current_cart": [],    # 5.4.3 current cart
            "state": STATE_BROWSING,
            "last_products_viewed": [],
            "pending_clarification": None,  # 5.3 ambiguity resolution
            "updated_at": None,
        }

    # ------------------------------------------------------------------
    # 5.4.2 Maintain last 5 messages
    # ------------------------------------------------------------------

    def add_message(self, user_id: int | str, role: str, content: str) -> dict:
        """Add a message to the conversation history (max 5)."""
        context = self.get_context(user_id)
        messages = context.get("last_messages", [])
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep only last 5
        context["last_messages"] = messages[-5:]
        self.save_context(user_id, context)
        return context

    # ------------------------------------------------------------------
    # 5.4.3 Track current cart
    # ------------------------------------------------------------------

    def add_to_cart(self, user_id: int | str, item: dict) -> dict:
        """Add a matched product to the cart."""
        context = self.get_context(user_id)
        cart = context.get("current_cart", [])

        # Check if product already in cart — update quantity
        product_id = item.get("product_id")
        for existing in cart:
            if existing.get("product_id") == product_id:
                existing["quantity"] = existing.get("quantity", 0) + item.get("quantity", 1)
                context["current_cart"] = cart
                self.save_context(user_id, context)
                return context

        cart.append(item)
        context["current_cart"] = cart
        context["state"] = STATE_ORDERING
        self.save_context(user_id, context)
        return context

    def clear_cart(self, user_id: int | str) -> None:
        """Clear the cart after order is placed."""
        context = self.get_context(user_id)
        context["current_cart"] = []
        context["state"] = STATE_BROWSING
        self.save_context(user_id, context)

    def get_cart(self, user_id: int | str) -> list:
        return self.get_context(user_id).get("current_cart", [])

    # ------------------------------------------------------------------
    # 5.6.2 State machine transitions
    # ------------------------------------------------------------------

    def set_state(self, user_id: int | str, state: str) -> None:
        context = self.get_context(user_id)
        context["state"] = state
        self.save_context(user_id, context)

    def get_state(self, user_id: int | str) -> str:
        return self.get_context(user_id).get("state", STATE_BROWSING)

    # ------------------------------------------------------------------
    # 5.3 Ambiguity resolution — store pending clarification
    # ------------------------------------------------------------------

    def set_pending_clarification(self, user_id: int | str, clarification: dict) -> None:
        """
        Store ambiguous match info so we can resolve it when user replies.
        clarification = {
            "item": parsed_item,
            "options": [product1, product2, ...],
            "remaining_items": [...],  # other items still to process
        }
        """
        context = self.get_context(user_id)
        context["pending_clarification"] = clarification
        context["state"] = STATE_AWAITING_CLARIFICATION
        self.save_context(user_id, context)

    def get_pending_clarification(self, user_id: int | str) -> dict | None:
        return self.get_context(user_id).get("pending_clarification")

    def clear_pending_clarification(self, user_id: int | str) -> None:
        context = self.get_context(user_id)
        context["pending_clarification"] = None
        self.save_context(user_id, context)

    # ------------------------------------------------------------------
    # 5.5.1 / 5.5.2 Smart features — last order / usual order
    # ------------------------------------------------------------------

    def get_last_order_suggestion(self, customer_id: str, supabase_client) -> list | None:
        """
        5.5.1 Fetch the customer's last order items for "Same as last time?" suggestion.
        Returns list of order items or None if no previous orders.
        """
        try:
            result = (
                supabase_client.table("orders")
                .select("id, order_items(product_id, product_name, quantity, unit_price)")
                .eq("customer_id", customer_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            orders = result.data or []
            if not orders:
                return None
            items = orders[0].get("order_items") or []
            return items if items else None
        except Exception as exc:
            logger.error("get_last_order_suggestion error: %s", exc)
            return None

    def get_usual_order(self, customer_id: str, supabase_client) -> list | None:
        """
        5.5.2 Determine the customer's "usual order" based on most frequently ordered items.
        Returns top 3 most ordered products or None.
        """
        try:
            result = (
                supabase_client.table("order_items")
                .select("product_id, product_name, quantity")
                .eq("orders.customer_id", customer_id)
                .execute()
            )
            items = result.data or []
            if not items:
                return None

            # Count frequency per product
            freq: dict[str, dict] = {}
            for item in items:
                pid = item.get("product_id")
                if pid:
                    if pid not in freq:
                        freq[pid] = {"product_name": item.get("product_name"), "count": 0, "product_id": pid}
                    freq[pid]["count"] += 1

            if not freq:
                return None

            # Return top 3
            top = sorted(freq.values(), key=lambda x: x["count"], reverse=True)[:3]
            return top
        except Exception as exc:
            logger.error("get_usual_order error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # 5.5.3 Handle order modifications
    # ------------------------------------------------------------------

    def modify_cart_item(self, user_id: int | str, product_id: str, new_quantity: float) -> bool:
        """Modify quantity of an item in the cart. Returns True if found and updated."""
        context = self.get_context(user_id)
        cart = context.get("current_cart", [])
        for item in cart:
            if item.get("product_id") == product_id:
                if new_quantity <= 0:
                    cart.remove(item)
                else:
                    item["quantity"] = new_quantity
                context["current_cart"] = cart
                self.save_context(user_id, context)
                return True
        return False

    def remove_from_cart(self, user_id: int | str, product_id: str) -> bool:
        """Remove an item from the cart."""
        return self.modify_cart_item(user_id, product_id, 0)

    # ------------------------------------------------------------------
    # Cart summary helper
    # ------------------------------------------------------------------

    def format_cart_summary(self, cart: list) -> str:
        """Format cart items as a readable string."""
        if not cart:
            return "Your cart is empty."
        lines = ["🛒 *Your Cart:*\n"]
        total = 0.0
        for i, item in enumerate(cart, 1):
            name = item.get("product_name", item.get("name", "Unknown"))
            qty = item.get("quantity", 1)
            unit = item.get("unit", "pcs")
            price = float(item.get("unit_price", item.get("price", 0)))
            subtotal = qty * price
            total += subtotal
            lines.append(f"{i}. {name} — {qty} {unit} × ₹{price} = ₹{subtotal:.0f}")
        lines.append(f"\n*Total: ₹{total:.0f}*")
        return "\n".join(lines)
