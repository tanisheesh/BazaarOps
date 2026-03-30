"""
Customer Lifecycle Agent (Telegram)
Handles birthday wishes automation and re-engagement messages via Telegram.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone, timedelta

from anthropic import Anthropic
from telegram import Bot
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)
bot = Bot(token=os.getenv("CUSTOMER_BOT_TOKEN", ""))


# ---------------------------------------------------------------------------
# 3.3 Birthday Wishes Automation
# ---------------------------------------------------------------------------

async def send_birthday_wishes(store_id: str | None = None) -> dict:
    """
    Daily cron job: query customers with today's birthday and send AI-generated
    personalized messages via Telegram.  Logs each wish in birthday_wishes_sent.

    Args:
        store_id: If provided, only process customers for that store.
                  If None, process all stores.

    Returns:
        dict with sent_count and skipped_count.
    """
    today = datetime.now().strftime("%m-%d")  # MM-DD format
    sent_count = 0
    skipped_count = 0

    try:
        # 3.3.2 Query customers with today's birthday
        query = (
            supabase.table("customers")
            .select("id, name, telegram_chat_id, store_id, stores(name)")
            .eq("birthday", today)
        )
        if store_id:
            query = query.eq("store_id", store_id)

        customers_result = query.execute()
        customers = customers_result.data or []

        for customer in customers:
            chat_id = customer.get("telegram_chat_id")
            if not chat_id:
                skipped_count += 1
                continue

            # Check if we already sent a wish today
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            already_sent = (
                supabase.table("birthday_wishes_sent")
                .select("id")
                .eq("customer_id", customer["id"])
                .gte("sent_at", today_start)
                .execute()
            )
            if already_sent.data:
                skipped_count += 1
                continue

            store_name = (
                customer["stores"]["name"]
                if customer.get("stores")
                else "our store"
            )

            # 3.3.3 Generate personalized message with AI
            message_text = await _generate_birthday_message(
                customer["name"], store_name
            )

            # 3.3.4 Send via Telegram
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown",
                )

                # 3.3.5 Log in birthday_wishes_sent table
                supabase.table("birthday_wishes_sent").insert(
                    {
                        "customer_id": customer["id"],
                        "message_text": message_text,
                        "responded": False,
                    }
                ).execute()

                sent_count += 1
                print(f"🎂 Birthday wish sent to {customer['name']}")

            except Exception as send_exc:
                print(f"❌ Failed to send birthday wish to {customer['name']}: {send_exc}")
                skipped_count += 1

    except Exception as exc:
        print(f"❌ send_birthday_wishes error: {exc}")

    print(f"🎂 Birthday wishes: {sent_count} sent, {skipped_count} skipped")
    return {"sent_count": sent_count, "skipped_count": skipped_count}


async def _generate_birthday_message(customer_name: str, store_name: str) -> str:
    """Use Claude to generate a warm, personalized birthday message."""
    try:
        prompt = (
            f"Write a short, warm birthday message for a customer named {customer_name} "
            f"from {store_name}. Keep it friendly, personal, and under 3 sentences. "
            f"Include a birthday emoji. Do NOT offer any discounts or promotions."
        )
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        print(f"⚠️ AI message generation failed, using fallback: {exc}")
        return (
            f"🎂 Happy Birthday, {customer_name}! "
            f"Wishing you a wonderful day from all of us at {store_name}! 🎉"
        )


# ---------------------------------------------------------------------------
# 3.3.6 Track redemption rate
# ---------------------------------------------------------------------------

async def get_birthday_redemption_rate(store_id: str) -> dict:
    """Return birthday wish stats and redemption rate for a store."""
    try:
        # Get all wishes for customers in this store
        result = (
            supabase.table("birthday_wishes_sent")
            .select("id, responded, customers!inner(store_id)")
            .eq("customers.store_id", store_id)
            .execute()
        )
        wishes = result.data or []
        total = len(wishes)
        responded = sum(1 for w in wishes if w.get("responded"))
        rate = (responded / total * 100) if total > 0 else 0.0
        return {
            "total_wishes": total,
            "responded": responded,
            "redemption_rate_pct": round(rate, 1),
        }
    except Exception as exc:
        print(f"❌ get_birthday_redemption_rate error: {exc}")
        return {"total_wishes": 0, "responded": 0, "redemption_rate_pct": 0.0}


# ---------------------------------------------------------------------------
# 3.5 Re-engagement via Telegram
# ---------------------------------------------------------------------------

async def run_re_engagement(store_id: str) -> dict:
    """
    3.5.2 Send first re-engagement message to at-risk customers.
    3.5.3 Send follow-up to those who didn't respond after 7 days.
    """
    sent_first = 0
    sent_followup = 0

    try:
        # --- First messages for newly detected at-risk customers ---
        at_risk_result = (
            supabase.table("customers")
            .select("id, name, telegram_chat_id, churn_risk_level, last_order_date")
            .eq("store_id", store_id)
            .not_.is_("churn_risk_level", "null")
            .execute()
        )
        at_risk_customers = at_risk_result.data or []

        for customer in at_risk_customers:
            chat_id = customer.get("telegram_chat_id")
            if not chat_id:
                continue

            # Check if we already sent a first message recently (within 7 days)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            existing = (
                supabase.table("re_engagement_messages")
                .select("id")
                .eq("customer_id", customer["id"])
                .eq("store_id", store_id)
                .gte("sent_at", cutoff)
                .execute()
            )
            if existing.data:
                continue  # Already messaged recently

            last_order_raw = customer.get("last_order_date")
            days_since = 0
            if last_order_raw:
                last_order_date = datetime.fromisoformat(
                    last_order_raw.replace("Z", "+00:00")
                )
                days_since = (datetime.now(timezone.utc) - last_order_date).days

            # 3.5.1 Generate personalized message (no discounts)
            message_text = _generate_reengagement_message(
                customer["name"], days_since, message_number=1
            )

            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown",
                )
                supabase.table("re_engagement_messages").insert(
                    {
                        "customer_id": customer["id"],
                        "store_id": store_id,
                        "message_number": 1,
                        "message_text": message_text,
                        "responded": False,
                    }
                ).execute()
                sent_first += 1
                print(f"📨 Re-engagement msg 1 sent to {customer['name']}")
            except Exception as send_exc:
                print(f"❌ Failed to send re-engagement to {customer['name']}: {send_exc}")

        # --- 3.5.3 Follow-up messages for non-responders after 7 days ---
        followup_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        pending_result = (
            supabase.table("re_engagement_messages")
            .select("id, customer_id, customers(name, telegram_chat_id, last_order_date)")
            .eq("store_id", store_id)
            .eq("message_number", 1)
            .eq("responded", False)
            .lte("sent_at", followup_cutoff)
            .execute()
        )
        pending_followups = pending_result.data or []

        for record in pending_followups:
            # Check we haven't already sent message 2
            already_followup = (
                supabase.table("re_engagement_messages")
                .select("id")
                .eq("customer_id", record["customer_id"])
                .eq("store_id", store_id)
                .eq("message_number", 2)
                .execute()
            )
            if already_followup.data:
                continue

            customer = record.get("customers", {})
            chat_id = customer.get("telegram_chat_id")
            if not chat_id:
                continue

            last_order_raw = customer.get("last_order_date")
            days_since = 0
            if last_order_raw:
                last_order_date = datetime.fromisoformat(
                    last_order_raw.replace("Z", "+00:00")
                )
                days_since = (datetime.now(timezone.utc) - last_order_date).days

            message_text = _generate_reengagement_message(
                customer.get("name", "there"), days_since, message_number=2
            )

            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown",
                )
                supabase.table("re_engagement_messages").insert(
                    {
                        "customer_id": record["customer_id"],
                        "store_id": store_id,
                        "message_number": 2,
                        "message_text": message_text,
                        "responded": False,
                    }
                ).execute()
                sent_followup += 1
                print(f"📨 Re-engagement follow-up sent to {customer.get('name')}")
            except Exception as send_exc:
                print(f"❌ Failed to send follow-up: {send_exc}")

    except Exception as exc:
        print(f"❌ run_re_engagement error: {exc}")

    print(
        f"📨 Re-engagement: {sent_first} first messages, {sent_followup} follow-ups"
    )
    return {"sent_first": sent_first, "sent_followup": sent_followup}


def _generate_reengagement_message(
    customer_name: str, days_since: int, message_number: int = 1
) -> str:
    """Return a personalized re-engagement message without discounts."""
    if message_number == 1:
        return (
            f"Hi {customer_name}! 👋 We miss you at the store. "
            f"It's been a while since your last order. "
            f"We have fresh stock waiting for you – come back and shop anytime! 🛒"
        )
    return (
        f"Hey {customer_name}! 😊 Just checking in – we haven't seen you in "
        f"{days_since} days. Your favourite products are still available. "
        f"We'd love to have you back! 🌟"
    )


# ---------------------------------------------------------------------------
# 3.5.4 Track response rate
# ---------------------------------------------------------------------------

async def get_reengagement_response_rate(store_id: str) -> dict:
    """Return re-engagement message stats and response rate for a store."""
    try:
        result = (
            supabase.table("re_engagement_messages")
            .select("id, responded, message_number")
            .eq("store_id", store_id)
            .execute()
        )
        messages = result.data or []
        total = len(messages)
        responded = sum(1 for m in messages if m.get("responded"))
        rate = (responded / total * 100) if total > 0 else 0.0
        return {
            "total_messages": total,
            "responded": responded,
            "response_rate_pct": round(rate, 1),
        }
    except Exception as exc:
        print(f"❌ get_reengagement_response_rate error: {exc}")
        return {"total_messages": 0, "responded": 0, "response_rate_pct": 0.0}


# ---------------------------------------------------------------------------
# Orchestrator: run all lifecycle jobs for a store
# ---------------------------------------------------------------------------

async def run_lifecycle_jobs(store_id: str) -> None:
    """Run VIP detection, churn prediction, and re-engagement for a store."""
    # Import here to avoid circular imports at module level
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "agent-service"))

    try:
        from agents.customer_lifecycle_agent import VIPDetector, ChurnPredictor
        vip = VIPDetector()
        vip.update_vip_flags(store_id)

        churn = ChurnPredictor()
        churn.update_churn_risk(store_id)
    except ImportError:
        print("⚠️ Could not import agent-service lifecycle agent – skipping VIP/churn update")

    await run_re_engagement(store_id)


if __name__ == "__main__":
    import asyncio

    if len(sys.argv) < 2:
        print("Usage: python customer_lifecycle_agent.py <store_id>")
        sys.exit(1)

    store_id_arg = sys.argv[1]
    asyncio.run(run_lifecycle_jobs(store_id_arg))
