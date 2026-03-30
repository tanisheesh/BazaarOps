"""
EventLogger: persists domain events to the event_log database table.

Uses psycopg2 with a SimpleConnectionPool for efficient connection reuse.
All database errors are caught and logged so the caller is never crashed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from events.event_types import Event

logger = logging.getLogger(__name__)


class EventLogger:
    """Logs events to the event_log table and tracks their processing status."""

    def __init__(self, database_url: str | None = None) -> None:
        """
        Args:
            database_url: PostgreSQL connection string. Falls back to the
                          DATABASE_URL environment variable when not provided.
        """
        url = database_url or os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError("database_url must be provided or DATABASE_URL env var must be set")

        self._pool = SimpleConnectionPool(minconn=1, maxconn=5, dsn=url)
        logger.info("EventLogger connection pool initialised.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_conn(self):
        return self._pool.getconn()

    def _put_conn(self, conn, close: bool = False) -> None:
        self._pool.putconn(conn, close=close)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_event(self, event: Event, status: str = "received") -> None:
        """Insert an event into the event_log table.

        Args:
            event:  The Event to persist.
            status: Initial processing status (default: 'received').
        """
        sql = """
            INSERT INTO event_log
                (event_id, event_type, store_id, data, metadata, processing_status)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO NOTHING;
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(sql, (
                    event.event_id,
                    event.event_type.value if hasattr(event.event_type, "value") else event.event_type,
                    event.store_id,
                    json.dumps(event.data),
                    json.dumps(event.metadata),
                    status,
                ))
            conn.commit()
            logger.debug("Logged event %s (status=%s)", event.event_id, status)
        except Exception as exc:
            logger.error("Failed to log event %s: %s", event.event_id, exc)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                self._put_conn(conn)

    def mark_processed(self, event_id: str) -> None:
        """Update an event's status to 'processed'.

        Args:
            event_id: The event_id of the event to update.
        """
        sql = """
            UPDATE event_log
            SET processing_status = 'processed', processed_at = NOW()
            WHERE event_id = %s;
        """
        self._update_status(event_id, sql, (event_id,))

    def mark_failed(self, event_id: str, error: str) -> None:
        """Update an event's status to 'failed' and record the error message.

        Args:
            event_id: The event_id of the event to update.
            error:    Description of the failure.
        """
        sql = """
            UPDATE event_log
            SET processing_status = 'failed', error_message = %s, processed_at = NOW()
            WHERE event_id = %s;
        """
        self._update_status(event_id, sql, (error, event_id))

    def get_recent_events(self, store_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch the most recent events for a given store.

        Args:
            store_id: UUID string of the store.
            limit:    Maximum number of rows to return (default: 100).

        Returns:
            List of dicts with event_log row data, ordered newest-first.
        """
        sql = """
            SELECT id, event_id, event_type, store_id, data, metadata,
                   processed_at, processing_status, error_message
            FROM event_log
            WHERE store_id = %s
            ORDER BY processed_at DESC
            LIMIT %s;
        """
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (store_id, limit))
                rows = cur.fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("Failed to fetch recent events for store %s: %s", store_id, exc)
            return []
        finally:
            if conn:
                self._put_conn(conn)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _update_status(self, event_id: str, sql: str, params: tuple) -> None:
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            logger.debug("Updated status for event %s", event_id)
        except Exception as exc:
            logger.error("Failed to update status for event %s: %s", event_id, exc)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                self._put_conn(conn)

    def close(self) -> None:
        """Close all connections in the pool."""
        try:
            self._pool.closeall()
            logger.info("EventLogger connection pool closed.")
        except Exception as exc:
            logger.warning("Error closing connection pool: %s", exc)
