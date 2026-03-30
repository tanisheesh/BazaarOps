"""
NLP Order Parser - Conversational AI Shopping Assistant
Task 5.1: NLP Pipeline (intent detection, entity extraction, Hindi/English mix)
Task 5.2: Product matching with fuzzy algorithm (threshold 70%)
Task 5.3: Ambiguity resolution
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hindi/English unit mappings (5.1.4)
# ---------------------------------------------------------------------------

HINDI_UNIT_MAP = {
    "kilo": "kg",
    "kilo gram": "kg",
    "kilogram": "kg",
    "kg": "kg",
    "gram": "g",
    "gm": "g",
    "grm": "g",
    "litre": "l",
    "liter": "l",
    "lt": "l",
    "ltr": "l",
    "piece": "pcs",
    "pcs": "pcs",
    "packet": "pkt",
    "pkt": "pkt",
    "dozen": "doz",
    "doz": "doz",
    # Hindi words
    "kilo": "kg",
    "kila": "kg",
    "kile": "kg",
    "kili": "kg",
    "graam": "g",
    "litr": "l",
    "nag": "pcs",
    "nag": "pcs",
}

HINDI_PRODUCT_MAP = {
    "chawal": "rice",
    "chaawal": "rice",
    "chawl": "rice",
    "cheeni": "sugar",
    "chini": "sugar",
    "shakkar": "sugar",
    "atta": "wheat flour",
    "aata": "wheat flour",
    "maida": "refined flour",
    "dal": "lentils",
    "daal": "lentils",
    "tel": "oil",
    "namak": "salt",
    "mirch": "chilli",
    "mirchi": "chilli",
    "haldi": "turmeric",
    "dhaniya": "coriander",
    "jeera": "cumin",
    "adrak": "ginger",
    "lahsun": "garlic",
    "pyaz": "onion",
    "pyaaz": "onion",
    "aloo": "potato",
    "tamatar": "tomato",
    "doodh": "milk",
    "ghee": "ghee",
    "makhan": "butter",
    "paneer": "paneer",
    "sabzi": "vegetables",
    "sabji": "vegetables",
}


def normalize_hindi_english(text: str) -> str:
    """Normalize Hindi words to English equivalents for better matching."""
    text_lower = text.lower()
    for hindi, english in HINDI_PRODUCT_MAP.items():
        text_lower = re.sub(r"\b" + hindi + r"\b", english, text_lower)
    for hindi_unit, eng_unit in HINDI_UNIT_MAP.items():
        text_lower = re.sub(r"\b" + hindi_unit + r"\b", eng_unit, text_lower)
    return text_lower


# ---------------------------------------------------------------------------
# 5.1.1 ConversationalOrderParser using Claude API
# ---------------------------------------------------------------------------

class ConversationalOrderParser:
    """
    Uses Claude API to parse natural language orders.
    Handles intent detection (5.1.2) and entity extraction (5.1.3).
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — NLP parser will be unavailable")
            self.claude_client = None
        else:
            self.claude_client = Anthropic(api_key=api_key)

        # NLP performance monitoring (5.10)
        self._parse_count = 0
        self._parse_errors = 0
        self._total_latency_ms = 0.0

    # ------------------------------------------------------------------
    # 5.1.2 Intent detection + 5.1.3 Entity extraction
    # ------------------------------------------------------------------

    async def parse_order(self, user_message: str, context: dict | None = None) -> dict:
        """
        Parse a natural language order message.

        Returns:
            {
                "intent": "place_order" | "ask_question" | "check_status" | "modify_order" | "unknown",
                "items": [{"product": str, "quantity": float, "unit": str}],
                "raw_message": str,
                "normalized_message": str,
            }
        """
        # 5.1.4 Normalize Hindi/English mix first
        normalized = normalize_hindi_english(user_message)

        if self.claude_client is None:
            return self._fallback_parse(user_message, normalized)

        context_str = ""
        if context and context.get("last_messages"):
            recent = context["last_messages"][-3:]
            context_str = "\nRecent conversation:\n" + "\n".join(
                f"- {m.get('role', 'user')}: {m.get('content', '')}" for m in recent
            )

        prompt = f"""Parse this customer order message and extract products, quantities, and units.
The customer may use Hindi words mixed with English (e.g., "2 kilo chawal" means "2 kg rice").
{context_str}

Message: "{user_message}"
Normalized: "{normalized}"

Return ONLY valid JSON (no markdown, no explanation):
{{
    "intent": "place_order" | "ask_question" | "check_status" | "modify_order" | "unknown",
    "items": [
        {{"product": "rice", "quantity": 2, "unit": "kg"}},
        {{"product": "sugar", "quantity": 1, "unit": "kg"}}
    ]
}}

Rules:
- intent "place_order": customer wants to buy something
- intent "ask_question": customer is asking about products/prices/availability
- intent "check_status": customer wants to know order status
- intent "modify_order": customer wants to change a previous order
- If no quantity mentioned, default to 1
- If no unit mentioned, use "pcs"
- Translate Hindi product names to English
"""

        start_ms = time.monotonic() * 1000
        try:
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            latency = time.monotonic() * 1000 - start_ms
            self._total_latency_ms += latency
            self._parse_count += 1

            raw_text = response.content[0].text.strip()
            # Strip markdown code fences if present
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)

            parsed = json.loads(raw_text)
            parsed["raw_message"] = user_message
            parsed["normalized_message"] = normalized
            return parsed

        except json.JSONDecodeError as exc:
            logger.error("parse_order: JSON decode error: %s", exc)
            self._parse_errors += 1
            return self._fallback_parse(user_message, normalized)
        except Exception as exc:
            logger.error("parse_order: Claude API error: %s", exc)
            self._parse_errors += 1
            return self._fallback_parse(user_message, normalized)

    def _fallback_parse(self, user_message: str, normalized: str) -> dict:
        """
        5.9 Fallback regex-based parser when Claude API is unavailable.
        Handles simple patterns like "2kg rice", "1 litre milk".
        """
        items = []
        # Pattern: optional number + optional unit + product name
        pattern = r"(\d+(?:\.\d+)?)\s*(kg|g|l|ltr|litre|liter|pcs|pkt|doz|kilo|gram|piece|packet)?\s+([a-zA-Z\s]+?)(?:,|and|$)"
        matches = re.findall(pattern, normalized, re.IGNORECASE)

        for qty_str, unit, product in matches:
            product = product.strip()
            if not product:
                continue
            unit = unit.lower() if unit else "pcs"
            unit = HINDI_UNIT_MAP.get(unit, unit)
            items.append({
                "product": product,
                "quantity": float(qty_str),
                "unit": unit,
            })

        intent = "place_order" if items else "unknown"
        # Simple keyword detection
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["status", "where", "delivered", "when"]):
            intent = "check_status"
        elif any(w in msg_lower for w in ["price", "cost", "how much", "available", "stock"]):
            intent = "ask_question"

        return {
            "intent": intent,
            "items": items,
            "raw_message": user_message,
            "normalized_message": normalized,
            "fallback": True,
        }

    # ------------------------------------------------------------------
    # 5.2 Product matching with fuzzy algorithm
    # ------------------------------------------------------------------

    def match_products(self, parsed_items: list[dict], store_products: list[dict]) -> list[dict]:
        """
        5.2.1 Fuzzy matching against store products.
        5.2.2 Handles typos and variations.
        5.2.3 Threshold: 70%.

        Returns list of match results:
            {
                "item": original parsed item,
                "matches": [{"product": ..., "score": int}],  # sorted by score desc
                "status": "matched" | "ambiguous" | "not_found",
            }
        """
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            logger.warning("fuzzywuzzy not installed — using simple string matching")
            return self._simple_match_products(parsed_items, store_products)

        results = []
        THRESHOLD = 70

        for item in parsed_items:
            query = item.get("product", "").lower().strip()
            candidates = []

            for product in store_products:
                name = product.get("name", "").lower()
                # Use multiple fuzz strategies and take the best
                score = max(
                    fuzz.ratio(query, name),
                    fuzz.partial_ratio(query, name),
                    fuzz.token_sort_ratio(query, name),
                    # Also compare against individual words in the product name
                    max((fuzz.ratio(query, word) for word in name.split()), default=0),
                )
                if score >= THRESHOLD:
                    candidates.append({"product": product, "score": score})

            candidates.sort(key=lambda x: x["score"], reverse=True)

            if not candidates:
                status = "not_found"
            elif len(candidates) == 1:
                status = "matched"
            else:
                # 5.3.1 Multiple matches → ambiguous
                status = "ambiguous"

            results.append({
                "item": item,
                "matches": candidates,
                "status": status,
            })

        return results

    def _simple_match_products(self, parsed_items: list[dict], store_products: list[dict]) -> list[dict]:
        """Simple substring matching fallback when fuzzywuzzy is unavailable."""
        results = []
        for item in parsed_items:
            query = item.get("product", "").lower().strip()
            candidates = []
            for product in store_products:
                name = product.get("name", "").lower()
                if query in name or name in query:
                    # Rough score based on length similarity
                    score = int(min(len(query), len(name)) / max(len(query), len(name), 1) * 100)
                    if score >= 70:
                        candidates.append({"product": product, "score": score})
            candidates.sort(key=lambda x: x["score"], reverse=True)
            status = "not_found" if not candidates else ("ambiguous" if len(candidates) > 1 else "matched")
            results.append({"item": item, "matches": candidates, "status": status})
        return results

    # ------------------------------------------------------------------
    # 5.10 NLP performance monitoring
    # ------------------------------------------------------------------

    def get_performance_metrics(self) -> dict:
        """Return NLP performance metrics for monitoring."""
        avg_latency = (
            self._total_latency_ms / self._parse_count if self._parse_count > 0 else 0.0
        )
        error_rate = (
            self._parse_errors / self._parse_count * 100 if self._parse_count > 0 else 0.0
        )
        return {
            "total_parses": self._parse_count,
            "total_errors": self._parse_errors,
            "error_rate_pct": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 1),
        }
