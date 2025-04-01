"""
Smart Notification Orchestrator
Handles timing optimization, fatigue prevention, message batching,
personalization, and performance monitoring for customer notifications.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Priority levels (higher = more important)
PRIORITY_CRITICAL = 4
PRIORITY_HIGH = 3
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 1

PRIORITY_LABELS = {
    PRIORITY_CRITICAL: "critical",
    PRIORITY_HIGH: "high",
    PRIORITY_MEDIUM: "medium",
    PRIORITY_LOW: "low",
}

PRIORITY_FROM_LABEL = {v: k for k, v in PRIORITY_LABELS.items()}

# 8.1.3 Only send between 9 AM and 9 PM
SEND_WINDOW_START = 9   # 9 AM
SEND_WINDOW_END = 21    # 9 PM

# 8.2.1 Max messages per customer per day
MAX_MESSAGES_PER_DAY = 3


def _get_supabase():
    from supabase import create_client
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )


# ---------------------------------------------------------------------------
# 8.1 Timing Optimization
# ---------------------------------------------------------------------------

def track_response_time(
    customer_id: str,
    notification_id: str,
    sent_at: datetime,
    responded_at: datetime,
    db_conn=None,
) -> bool:
    """
    8.1.1 Track when a customer responds to a notification.
    Stores the response hour for learning optimal send times.
    """
    supabase = db_conn or _get_supabase()
    try:
        response_hour = sent_at.hour
        supabase.table("notification_history").update(
            {
                "responded": True,
                "responded_at": responded_at.isoformat(),
                "response_hour": response_hour,
            }
        ).eq("id", notification_id).execute()
        return True
    except Exception as exc:
        logger.error("track_response_time error: %s", exc)
        return False


def get_optimal_send_time(customer_id: str, db_conn=None) -> str:
    """
    8.1.2 Learn optimal notification time per customer by analyzing response patterns.
    8.1.3 Defaults to 18:00 if no data; always within 9 AM - 9 PM window.
    Returns HH:MM string (24h).
    """
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_history")
            .select("response_hour")
            .eq("customer_id", customer_id)
            .eq("responded", True)
            .not_.is_("response_hour", "null")
            .execute()
        )
        rows = result.data or []

        if not rows:
            return "18:00"

        # Count responses per hour
        hour_counts: dict[int, int] = {}
        for row in rows:
            h = row.get("response_hour")
            if h is not None:
                hour_counts[h] = hour_counts.get(h, 0) + 1

        if not hour_counts:
            return "18:00"

        # 8.1.2 Find hour with most responses
        best_hour = max(hour_counts, key=hour_counts.get)

        # 8.1.3 Enforce 9 AM - 9 PM window
        best_hour = max(SEND_WINDOW_START, min(SEND_WINDOW_END - 1, best_hour))
        return f"{best_hour:02d}:00"

    except Exception as exc:
        logger.error("get_optimal_send_time error: %s", exc)
        return "18:00"


def is_within_send_window(hour: int) -> bool:
    """8.1.3 Return True if the given hour is within the 9 AM - 9 PM send window."""
    return SEND_WINDOW_START <= hour < SEND_WINDOW_END


# ---------------------------------------------------------------------------
# 8.2 Fatigue Prevention
# ---------------------------------------------------------------------------

def get_messages_sent_today(customer_id: str, db_conn=None) -> int:
    """Return the number of notifications sent to a customer today."""
    supabase = db_conn or _get_supabase()
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        result = (
            supabase.table("notification_history")
            .select("id")
            .eq("customer_id", customer_id)
            .gte("sent_at", today_start)
            .execute()
        )
        return len(result.data or [])
    except Exception as exc:
        logger.error("get_messages_sent_today error: %s", exc)
        return 0


def can_send_notification(customer_id: str, db_conn=None) -> bool:
    """
    8.2.1 Return True if the customer has received fewer than MAX_MESSAGES_PER_DAY today.
    """
    return get_messages_sent_today(customer_id, db_conn) < MAX_MESSAGES_PER_DAY


def get_priority_value(priority_label: str) -> int:
    """8.2.2 Convert priority label to numeric value (critical > high > medium > low)."""
    return PRIORITY_FROM_LABEL.get(priority_label.lower(), PRIORITY_LOW)


def queue_notification(
    customer_id: str,
    message: str,
    priority: str = "medium",
    notification_type: str = "general",
    db_conn=None,
) -> Optional[str]:
    """
    8.2.3 Queue a non-urgent notification for later delivery.
    Returns the notification id.
    """
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_history")
            .insert(
                {
                    "customer_id": customer_id,
                    "message": message,
                    "priority": priority,
                    "notification_type": notification_type,
                    "status": "queued",
                    "responded": False,
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:
        logger.error("queue_notification error: %s", exc)
    return None


def get_pending_notifications(customer_id: str, db_conn=None) -> list[dict]:
    """Return all queued (unsent) notifications for a customer, ordered by priority desc."""
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_history")
            .select("*")
            .eq("customer_id", customer_id)
            .eq("status", "queued")
            .execute()
        )
        rows = result.data or []
        # Sort by priority descending (critical first)
        rows.sort(key=lambda r: get_priority_value(r.get("priority", "low")), reverse=True)
        return rows
    except Exception as exc:
        logger.error("get_pending_notifications error: %s", exc)
        return []


def mark_notifications_batched(notification_ids: list[str], db_conn=None) -> bool:
    """Mark a list of notifications as batched (consumed into a batch message)."""
    if not notification_ids:
        return True
    supabase = db_conn or _get_supabase()
    try:
        supabase.table("notification_history").update(
            {"status": "batched"}
        ).in_("id", notification_ids).execute()
        return True
    except Exception as exc:
        logger.error("mark_notifications_batched error: %s", exc)
        return False


def log_sent_notification(
    customer_id: str,
    message: str,
    notification_type: str = "batch",
    priority: str = "medium",
    db_conn=None,
) -> Optional[str]:
    """Record a sent notification in notification_history."""
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_history")
            .insert(
                {
                    "customer_id": customer_id,
                    "message": message,
                    "priority": priority,
                    "notification_type": notification_type,
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "responded": False,
                }
            )
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:
        logger.error("log_sent_notification error: %s", exc)
    return None


# ---------------------------------------------------------------------------
# 8.3 Message Batching
# ---------------------------------------------------------------------------

def combine_messages(notifications: list[dict]) -> str:
    """
    8.3.2 Combine multiple pending notifications into a single message.
    Higher-priority messages appear first.
    """
    if not notifications:
        return ""
    if len(notifications) == 1:
        return notifications[0].get("message", "")

    parts = []
    for i, notif in enumerate(notifications, start=1):
        msg = notif.get("message", "").strip()
        if msg:
            parts.append(f"{i}. {msg}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 8.4 Personalization
# ---------------------------------------------------------------------------

def get_notification_preferences(customer_id: str, db_conn=None) -> dict:
    """Fetch stored notification preferences for a customer."""
    supabase = db_conn or _get_supabase()
    try:
        result = (
            supabase.table("notification_preferences")
            .select("*")
            .eq("customer_id", customer_id)
            .single()
            .execute()
        )
        return result.data or {}
    except Exception as exc:
        logger.debug("get_notification_preferences: %s", exc)
        return {}


def detect_tone_preference(message_history: list[str]) -> str:
    """
    8.4.1 Detect customer tone preference (formal vs casual) from message history.
    Returns 'formal' or 'casual'.
    """
    if not message_history:
        return "casual"

    formal_indicators = ["please", "kindly", "sir", "madam", "regards", "sincerely"]
    casual_indicators = ["hey", "hi", "thanks", "cool", "ok", "okay", "yep", "nope"]

    formal_count = 0
    casual_count = 0

    for msg in message_history:
        lower = msg.lower()
        for word in formal_indicators:
            if word in lower:
                formal_count += 1
        for word in casual_indicators:
            if word in lower:
                casual_count += 1

    return "formal" if formal_count > casual_count else "casual"


def detect_emoji_preference(message_history: list[str]) -> bool:
    """
    8.4.2 Detect whether the customer uses emojis in their messages.
    Returns True if emojis are preferred.
    """
    if not message_history:
        return True  # Default: use emojis

    emoji_count = 0
    for msg in message_history:
        # Simple heuristic: check for common emoji unicode ranges
        for char in msg:
            cp = ord(char)
            if (
                0x1F600 <= cp <= 0x1F64F  # Emoticons
                or 0x1F300 <= cp <= 0x1F5FF  # Misc symbols
                or 0x1F680 <= cp <= 0x1F6FF  # Transport
                or 0x2600 <= cp <= 0x26FF    # Misc symbols
                or 0x2700 <= cp <= 0x27BF    # Dingbats
            ):
                emoji_count += 1

    return emoji_count > 0


def detect_language_preference(message_history: list[str]) -> str:
    """
    8.4.3 Detect language preference (Hindi vs English) from message history.
    Returns 'hindi' or 'english'.
    """
    if not message_history:
        return "english"

    hindi_indicators = [
        "kya", "hai", "nahi", "haan", "theek", "acha", "bhai",
        "didi", "ji", "rupaye", "paisa", "order", "chahiye",
        "mujhe", "humko", "aap", "tum",
    ]

    hindi_count = 0
    for msg in message_history:
        lower = msg.lower()
        for word in hindi_indicators:
            if word in lower:
                hindi_count += 1

    # Also check for Devanagari script
    devanagari_count = sum(
        1 for msg in message_history
        for char in msg
        if 0x0900 <= ord(char) <= 0x097F
    )

    return "hindi" if (hindi_count + devanagari_count) > len(message_history) else "english"


def detect_length_preference(message_history: list[str]) -> str:
    """
    8.4.4 Detect message length preference (brief vs detailed) from message history.
    Returns 'brief' or 'detailed'.
    """
    if not message_history:
        return "brief"

    avg_length = sum(len(m) for m in message_history) / len(message_history)
    return "detailed" if avg_length > 100 else "brief"


def personalize_message(
    message: str,
    tone: str = "casual",
    use_emojis: bool = True,
    language: str = "english",
    length: str = "brief",
) -> str:
    """
    Apply personalization to a message based on customer preferences.
    """
    result = message

    # 8.4.2 Remove emojis if customer prefers no emojis
    if not use_emojis:
        cleaned = []
        for char in result:
            cp = ord(char)
            if not (
                0x1F600 <= cp <= 0x1F64F
                or 0x1F300 <= cp <= 0x1F5FF
                or 0x1F680 <= cp <= 0x1F6FF
                or 0x2600 <= cp <= 0x26FF
                or 0x2700 <= cp <= 0x27BF
            ):
                cleaned.append(char)
        result = "".join(cleaned).strip()

    # 8.4.1 Adjust tone
    if tone == "formal":
        # Replace casual openers
        result = result.replace("Hey!", "Dear Customer,")
        result = result.replace("Hi!", "Dear Customer,")
        result = result.replace("Hey ", "Dear Customer, ")

    # 8.4.4 Truncate for brief preference
    if length == "brief" and len(result) > 200:
        result = result[:197] + "..."

    return result


def update_notification_preferences(
    customer_id: str,
    message_history: list[str],
    db_conn=None,
) -> dict:
    """
    8.4.1-8.4.4 Analyze message history and update notification preferences in DB.
    Returns the detected preferences dict.
    """
    tone = detect_tone_preference(message_history)
    use_emojis = detect_emoji_preference(message_history)
    language = detect_language_preference(message_history)
    length = detect_length_preference(message_history)

    prefs = {
        "customer_id": customer_id,
        "tone_preference": tone,
        "use_emojis": use_emojis,
        "language_preference": language,
        "message_length_preference": length,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase = db_conn or _get_supabase()
    try:
        # Upsert preferences
        existing = get_notification_preferences(customer_id, db_conn=supabase)
        if existing:
            supabase.table("notification_preferences").update(prefs).eq(
                "customer_id", customer_id
            ).execute()
        else:
            supabase.table("notification_preferences").insert(prefs).execute()
    except Exception as exc:
        logger.error("update_notification_preferences error: %s", exc)

    return prefs


# ---------------------------------------------------------------------------
# 8.7 Response Rate Metrics
# ---------------------------------------------------------------------------

def calculate_response_rate_metrics(
    store_id: str,
    days: int = 30,
    db_conn=None,
) -> dict:
    """
    8.7 Calculate response rate metrics for notifications sent to customers
    of a given store over the past `days` days.
    """
    supabase = db_conn or _get_supabase()
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # Get all sent notifications for the store's customers
        result = (
            supabase.table("notification_history")
            .select("id, customer_id, responded, priority, notification_type, sent_at")
            .eq("store_id", store_id)
            .eq("status", "sent")
            .gte("sent_at", since)
            .execute()
        )
        notifications = result.data or []

        total = len(notifications)
        if total == 0:
            return {
                "store_id": store_id,
                "period_days": days,
                "total_sent": 0,
                "total_responded": 0,
                "response_rate_pct": 0.0,
                "by_priority": {},
                "by_type": {},
            }

        responded = sum(1 for n in notifications if n.get("responded"))
        response_rate = round(responded / total * 100, 1)

        # Break down by priority
        by_priority: dict[str, dict] = {}
        for n in notifications:
            p = n.get("priority", "medium")
            if p not in by_priority:
                by_priority[p] = {"sent": 0, "responded": 0}
            by_priority[p]["sent"] += 1
            if n.get("responded"):
                by_priority[p]["responded"] += 1

        for p, stats in by_priority.items():
            stats["response_rate_pct"] = round(
                stats["responded"] / stats["sent"] * 100, 1
            ) if stats["sent"] > 0 else 0.0

        # Break down by type
        by_type: dict[str, dict] = {}
        for n in notifications:
            t = n.get("notification_type", "general")
            if t not in by_type:
                by_type[t] = {"sent": 0, "responded": 0}
            by_type[t]["sent"] += 1
            if n.get("responded"):
                by_type[t]["responded"] += 1

        for t, stats in by_type.items():
            stats["response_rate_pct"] = round(
                stats["responded"] / stats["sent"] * 100, 1
            ) if stats["sent"] > 0 else 0.0

        return {
            "store_id": store_id,
            "period_days": days,
            "total_sent": total,
            "total_responded": responded,
            "response_rate_pct": response_rate,
            "by_priority": by_priority,
            "by_type": by_type,
        }

    except Exception as exc:
        logger.error("calculate_response_rate_metrics error: %s", exc)
        return {"store_id": store_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# 8.8 Performance Monitoring
# ---------------------------------------------------------------------------

def get_notification_performance_metrics(
    store_id: str,
    days: int = 7,
    db_conn=None,
) -> dict:
    """
    8.8 Return performance tracking metrics for the notification system.
    Includes delivery rate, fatigue rate, batching rate, and timing compliance.
    """
    supabase = db_conn or _get_supabase()
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        result = (
            supabase.table("notification_history")
            .select("id, customer_id, status, priority, sent_at, responded, notification_type")
            .eq("store_id", store_id)
            .gte("created_at", since)
            .execute()
        )
        records = result.data or []

        total = len(records)
        if total == 0:
            return {
                "store_id": store_id,
                "period_days": days,
                "total_notifications": 0,
                "sent_count": 0,
                "queued_count": 0,
                "batched_count": 0,
                "delivery_rate_pct": 0.0,
                "batching_rate_pct": 0.0,
                "response_rate_pct": 0.0,
            }

        sent = [r for r in records if r.get("status") == "sent"]
        queued = [r for r in records if r.get("status") == "queued"]
        batched = [r for r in records if r.get("status") == "batched"]
        responded = [r for r in sent if r.get("responded")]

        delivery_rate = round(len(sent) / total * 100, 1) if total > 0 else 0.0
        batching_rate = round(len(batched) / total * 100, 1) if total > 0 else 0.0
        response_rate = round(len(responded) / len(sent) * 100, 1) if sent else 0.0

        # Count by priority
        priority_breakdown: dict[str, int] = {}
        for r in records:
            p = r.get("priority", "medium")
            priority_breakdown[p] = priority_breakdown.get(p, 0) + 1

        return {
            "store_id": store_id,
            "period_days": days,
            "total_notifications": total,
            "sent_count": len(sent),
            "queued_count": len(queued),
            "batched_count": len(batched),
            "delivery_rate_pct": delivery_rate,
            "batching_rate_pct": batching_rate,
            "response_rate_pct": response_rate,
            "priority_breakdown": priority_breakdown,
        }

    except Exception as exc:
        logger.error("get_notification_performance_metrics error: %s", exc)
        return {"store_id": store_id, "error": str(exc)}


# ---------------------------------------------------------------------------
# NotificationOrchestrator class
# ---------------------------------------------------------------------------

class NotificationOrchestrator:
    """
    Smart notification orchestrator that handles timing, fatigue prevention,
    batching, and personalization for customer notifications.
    """

    def __init__(self, supabase=None):
        self.supabase = supabase

    def get_optimal_time(self, customer_id: str) -> str:
        """
        8.1.2 Analyze past response times to find the best hour to send.
        8.1.3 Defaults to 18:00; always within 9 AM - 9 PM window.
        """
        return get_optimal_send_time(customer_id, db_conn=self.supabase)

    def combine_messages(self, notifications: list[dict]) -> str:
        """8.3.2 Combine multiple notifications into a single message."""
        return combine_messages(notifications)

    def batch_notifications(self, customer_id: str) -> Optional[dict]:
        """
        8.3 Collect pending notifications, combine into one message,
        and schedule at the optimal time.
        Returns the scheduled batch info or None if nothing to batch.
        """
        pending = get_pending_notifications(customer_id, db_conn=self.supabase)

        if not pending:
            return None

        # 8.3.2 Combine into single message
        combined = self.combine_messages(pending)

        # 8.3.3 Schedule at optimal time
        optimal_time = self.get_optimal_time(customer_id)

        # Mark originals as batched
        ids = [n["id"] for n in pending if n.get("id")]
        mark_notifications_batched(ids, db_conn=self.supabase)

        # Log the batch notification as queued for the optimal time
        batch_id = log_sent_notification(
            customer_id=customer_id,
            message=combined,
            notification_type="batch",
            priority=PRIORITY_LABELS.get(
                max(get_priority_value(n.get("priority", "low")) for n in pending),
                "medium",
            ),
            db_conn=self.supabase,
        )

        logger.info(
            "Batched %d notifications for customer %s at %s",
            len(pending),
            customer_id,
            optimal_time,
        )

        return {
            "customer_id": customer_id,
            "batch_id": batch_id,
            "message": combined,
            "scheduled_time": optimal_time,
            "notification_count": len(pending),
        }

    def send_notification(
        self,
        customer_id: str,
        message: str,
        priority: str = "medium",
        notification_type: str = "general",
    ) -> dict:
        """
        Send or queue a notification respecting fatigue limits and send window.
        Returns a dict with status and details.
        """
        now = datetime.now(timezone.utc)

        # 8.1.3 Check send window
        if not is_within_send_window(now.hour):
            notif_id = queue_notification(
                customer_id, message, priority, notification_type,
                db_conn=self.supabase,
            )
            return {
                "status": "queued",
                "reason": "outside_send_window",
                "notification_id": notif_id,
            }

        # 8.2.1 Check daily limit
        if not can_send_notification(customer_id, db_conn=self.supabase):
            # 8.2.3 Queue non-urgent notifications
            priority_val = get_priority_value(priority)
            if priority_val < PRIORITY_HIGH:
                notif_id = queue_notification(
                    customer_id, message, priority, notification_type,
                    db_conn=self.supabase,
                )
                return {
                    "status": "queued",
                    "reason": "daily_limit_reached",
                    "notification_id": notif_id,
                }
            # Critical/high priority: send anyway (override limit)

        # Apply personalization
        prefs = get_notification_preferences(customer_id, db_conn=self.supabase)
        personalized = personalize_message(
            message,
            tone=prefs.get("tone_preference", "casual"),
            use_emojis=prefs.get("use_emojis", True),
            language=prefs.get("language_preference", "english"),
            length=prefs.get("message_length_preference", "brief"),
        )

        notif_id = log_sent_notification(
            customer_id=customer_id,
            message=personalized,
            notification_type=notification_type,
            priority=priority,
            db_conn=self.supabase,
        )

        return {
            "status": "sent",
            "notification_id": notif_id,
            "message": personalized,
        }
