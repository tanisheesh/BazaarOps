"""
Reorder Agent - Orchestrates the full reorder workflow:
  inventory.low event → forecast → decision → approval request → supplier message
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import datetime, timezone

from supabase import create_client
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from agents.inventory_orchestrator import (
    DemandForecastingModule,
    LearningSystem,
    ReorderDecisionEngine,
)
from agents.message_bus.protocol import AgentMessage, AgentName, MessageType
from agents.message_bus.publisher import AgentMessagePublisher
from events.event_types import Event

logger = logging.getLogger(__name__)


def _get_supabase():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


class ReorderAgent:
    """
    Listens for INVENTORY_LOW events and drives the full reorder workflow.
    """

    def __init__(self, supabase_client=None, bot_token: str | None = None):
        self.supabase = supabase_client or _get_supabase()
        self.forecaster = DemandForecastingModule(self.supabase)
        self.decision_engine = ReorderDecisionEngine(self.supabase)
        self.learning = LearningSystem(self.supabase)
        _token = bot_token or os.getenv("OWNER_BOT_TOKEN", "")
        self.bot = Bot(token=_token) if _token else None
        self.message_bus = AgentMessagePublisher()
        logger.info("✅ ReorderAgent ready")

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    async def handle_inventory_low(self, event: Event) -> None:
        """Entry point called by the event subscriber."""
        logger.info("📦 INVENTORY_LOW event: %s", event.event_id)
        data = event.data or {}
        store_id = event.store_id
        product_id = data.get("product_id")
        current_stock = float(data.get("current_stock", 0))

        if not product_id:
            logger.warning("INVENTORY_LOW event missing product_id")
            return

        try:
            await self.process_reorder(store_id, product_id, current_stock)
        except Exception as exc:
            logger.error("ReorderAgent error: %s", exc)

    # ------------------------------------------------------------------
    # Core workflow
    # ------------------------------------------------------------------

    async def process_reorder(
        self, store_id: str, product_id: str, current_stock: float
    ) -> dict | None:
        """Run forecast → decision → approval request."""
        # Get product details
        product = self._get_product(product_id)
        if not product:
            logger.warning("Product %s not found", product_id)
            return None

        unit_cost = float(product.get("cost_price") or 0)

        # Forecast
        forecast = self.forecaster.run_forecast(store_id, product_id, days_history=30)

        # Apply learning adjustment
        pattern = self.learning.get_edit_pattern(store_id, product_id)
        avg_edit_pct = pattern.get("avg_edit_percentage", 0.0)

        # Decision
        decision = self.decision_engine.evaluate(
            store_id, product_id, current_stock, forecast, unit_cost
        )

        if not decision["needs_reorder"]:
            logger.info(
                "No reorder needed for %s (%.1f days left)",
                product.get("name"),
                decision.get("days_until_stockout") or 0,
            )
            return None

        # Adjust suggestion with learning
        raw_qty = decision["suggested_quantity"]
        adjusted_qty = self.learning.adjust_suggestion(raw_qty, avg_edit_pct)
        decision["suggested_quantity"] = adjusted_qty
        decision["estimated_cost"] = self.decision_engine.estimate_cost(
            adjusted_qty, unit_cost
        )

        # Persist pending order
        reorder_id = self._create_pending_order(
            store_id, product_id, adjusted_qty
        )
        if not reorder_id:
            return None

        # Send Telegram approval request
        await self._send_approval_request(
            store_id, product, current_stock, forecast, decision, reorder_id
        )

        return {
            "reorder_id": reorder_id,
            "product": product.get("name"),
            "suggested_quantity": adjusted_qty,
            "decision": decision,
            "forecast": forecast,
        }

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _get_product(self, product_id: str) -> dict | None:
        try:
            result = (
                self.supabase.table("products")
                .select("id, name, unit, cost_price, supplier_name, supplier_whatsapp")
                .eq("id", product_id)
                .single()
                .execute()
            )
            return result.data
        except Exception as exc:
            logger.error("_get_product error: %s", exc)
            return None

    def _create_pending_order(
        self, store_id: str, product_id: str, quantity: float
    ) -> str | None:
        """Insert into pending_supplier_orders and return the new id."""
        try:
            result = (
                self.supabase.table("pending_supplier_orders")
                .insert(
                    {
                        "store_id": store_id,
                        "product_id": product_id,
                        "quantity": quantity,
                        "suggested_by_agent": True,
                        "owner_approved": False,
                        "supplier_contacted": False,
                        "status": "pending",
                    }
                )
                .execute()
            )
            if result.data:
                return result.data[0]["id"]
        except Exception as exc:
            logger.error("_create_pending_order error: %s", exc)
        return None

    # ------------------------------------------------------------------
    # 2.3 Owner Approval via Telegram
    # ------------------------------------------------------------------

    async def _send_approval_request(
        self,
        store_id: str,
        product: dict,
        current_stock: float,
        forecast: dict,
        decision: dict,
        reorder_id: str,
    ) -> None:
        """Send Telegram message with Approve / Edit / Reject inline buttons."""
        if not self.bot:
            logger.warning("No Telegram bot configured – skipping approval request")
            return

        chat_id = self._get_store_chat_id(store_id)
        if not chat_id:
            logger.warning("No telegram_chat_id for store %s", store_id)
            return

        product_name = product.get("name", "Unknown")
        unit = product.get("unit", "unit")
        qty = decision["suggested_quantity"]
        cost = decision["estimated_cost"]
        days_left = decision.get("days_until_stockout")
        confidence = forecast.get("confidence_score", 0)
        trend = forecast.get("trend", "stable")

        days_text = f"{days_left:.1f}" if days_left is not None else "N/A"

        text = (
            f"🔔 *Reorder Approval Needed*\n\n"
            f"📦 *Product:* {product_name}\n"
            f"📊 *Current Stock:* {current_stock:.1f} {unit}\n"
            f"⏳ *Days Until Stockout:* {days_text}\n"
            f"📈 *Trend:* {trend.capitalize()}\n"
            f"🔮 *14-Day Forecast:* {forecast.get('forecast_14_days', 0):.1f} {unit}\n"
            f"📦 *Suggested Reorder:* {qty:.1f} {unit}\n"
            f"💰 *Estimated Cost:* ₹{cost:.2f}\n"
            f"🎯 *Confidence:* {confidence:.0f}%\n\n"
            f"Please review and take action:"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Approve", callback_data=f"reorder_approve:{reorder_id}"
                    ),
                    InlineKeyboardButton(
                        "✏️ Edit Qty", callback_data=f"reorder_edit:{reorder_id}"
                    ),
                    InlineKeyboardButton(
                        "❌ Reject", callback_data=f"reorder_reject:{reorder_id}"
                    ),
                ]
            ]
        )

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            logger.info("Approval request sent for reorder %s", reorder_id)
        except Exception as exc:
            logger.error("Failed to send approval request: %s", exc)

    def _get_store_chat_id(self, store_id: str) -> str | None:
        try:
            result = (
                self.supabase.table("stores")
                .select("telegram_chat_id")
                .eq("id", store_id)
                .single()
                .execute()
            )
            return result.data.get("telegram_chat_id") if result.data else None
        except Exception as exc:
            logger.error("_get_store_chat_id error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # 2.4 Supplier Communication
    # ------------------------------------------------------------------

    def generate_whatsapp_message(
        self,
        supplier_name: str,
        quantity: float,
        unit: str,
        product_name: str,
        expected_delivery: str | None = None,
    ) -> str:
        """Generate WhatsApp message template for supplier."""
        date_str = expected_delivery or "as soon as possible"
        return (
            f"Hi {supplier_name}, please send {quantity:.0f} {unit} of {product_name}. "
            f"Expected delivery: {date_str}"
        )

    async def contact_supplier(self, reorder_id: str) -> bool:
        """Generate WhatsApp link and mark supplier as contacted."""
        try:
            result = (
                self.supabase.table("pending_supplier_orders")
                .select(
                    "id, quantity, products(name, unit, supplier_name, supplier_whatsapp)"
                )
                .eq("id", reorder_id)
                .single()
                .execute()
            )
            if not result.data:
                return False

            order = result.data
            product = order.get("products", {})
            supplier_name = product.get("supplier_name", "Supplier")
            supplier_wa = product.get("supplier_whatsapp", "")
            qty = float(order["quantity"])
            unit = product.get("unit", "unit")
            product_name = product.get("name", "product")

            msg = self.generate_whatsapp_message(
                supplier_name, qty, unit, product_name
            )

            # Log the contact attempt
            self.supabase.table("pending_supplier_orders").update(
                {
                    "supplier_contacted": True,
                    "status": "supplier_contacted",
                }
            ).eq("id", reorder_id).execute()

            logger.info(
                "Supplier contact logged for reorder %s. WhatsApp: %s | Msg: %s",
                reorder_id,
                supplier_wa,
                msg,
            )
            return True
        except Exception as exc:
            logger.error("contact_supplier error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Approval handlers (called from Telegram callback or API)
    # ------------------------------------------------------------------

    async def approve_reorder(
        self, reorder_id: str, approved_quantity: float | None = None
    ) -> bool:
        """Approve a reorder, optionally with an edited quantity."""
        try:
            # Get current suggested quantity
            result = (
                self.supabase.table("pending_supplier_orders")
                .select("quantity")
                .eq("id", reorder_id)
                .single()
                .execute()
            )
            if not result.data:
                return False

            suggested_qty = float(result.data["quantity"])
            final_qty = approved_quantity if approved_quantity is not None else suggested_qty

            # Update order
            self.supabase.table("pending_supplier_orders").update(
                {
                    "owner_approved": True,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                    "quantity": final_qty,
                    "status": "approved",
                }
            ).eq("id", reorder_id).execute()

            # Record in learning system
            self.learning.record_edit(reorder_id, suggested_qty, final_qty)

            # Contact supplier
            await self.contact_supplier(reorder_id)
            return True
        except Exception as exc:
            logger.error("approve_reorder error: %s", exc)
            return False

    async def reject_reorder(self, reorder_id: str) -> bool:
        """Reject a pending reorder."""
        try:
            self.supabase.table("pending_supplier_orders").update(
                {"status": "rejected", "owner_approved": False}
            ).eq("id", reorder_id).execute()
            return True
        except Exception as exc:
            logger.error("reject_reorder error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # 7.3.3 Collaboration messaging
    # ------------------------------------------------------------------

    async def send_collaboration_message(
        self,
        to_agent: str,
        message_type: str,
        data: dict,
        priority: int = 5,
    ) -> None:
        """Publish a message to the agent message bus."""
        try:
            msg = AgentMessage(
                from_agent=AgentName.REORDER.value,
                to_agent=to_agent,
                message_type=message_type,
                data=data,
                priority=priority,
            )
            await self.message_bus.publish(msg)
        except Exception as exc:
            logger.error("ReorderAgent.send_collaboration_message error: %s", exc)

    async def publish_reorder_needed(
        self,
        product_id: str,
        suggested_quantity: float,
        estimated_cost: float,
        store_id: str = "",
    ) -> None:
        """7.3.3 Publish REORDER_NEEDED to coordinator."""
        await self.send_collaboration_message(
            to_agent=AgentName.COORDINATOR.value,
            message_type=MessageType.REORDER_NEEDED,
            data={
                "product_id": product_id,
                "suggested_quantity": suggested_quantity,
                "estimated_cost": estimated_cost,
                "store_id": store_id,
            },
            priority=8,
        )
