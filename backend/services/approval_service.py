import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings


DATABASE_PATH = Path(__file__).resolve().parent.parent / "approval_workflows.db"


@dataclass(frozen=True)
class ApprovalClaim:
    accepted: bool
    thread_id: str | None = None
    reason: str = ""


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_approval_db() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS email_approvals (
                token TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                approver_email TEXT NOT NULL,
                status TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                completed_at INTEGER
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS resend_webhook_events (
                event_id TEXT PRIMARY KEY,
                received_at INTEGER NOT NULL
            )
            """
        )


def create_pending_approval(token: str, thread_id: str) -> None:
    now = int(time.time())
    expires_at = now + settings.APPROVAL_TOKEN_TTL_SECONDS
    approver = (settings.APPROVAL_EMAIL or "").lower()
    with _connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO email_approvals
                (token, thread_id, approver_email, status, expires_at, created_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (token, thread_id, approver, expires_at, now),
        )


def claim_approval(
    *, token: str, sender_email: str, event_id: str
) -> ApprovalClaim:
    """Atomically reserve a single-use approval before resuming LangGraph."""
    now = int(time.time())
    connection = _connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = connection.execute(
            "SELECT 1 FROM resend_webhook_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if duplicate:
            connection.rollback()
            return ApprovalClaim(False, reason="duplicate_event")

        row = connection.execute(
            """
            SELECT thread_id, approver_email, status, expires_at
            FROM email_approvals WHERE token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            connection.rollback()
            return ApprovalClaim(False, reason="unknown_token")
        if row["approver_email"] != sender_email.lower():
            connection.rollback()
            return ApprovalClaim(False, reason="unauthorized_sender")
        if row["expires_at"] < now:
            connection.execute(
                "UPDATE email_approvals SET status = 'expired' WHERE token = ?", (token,)
            )
            connection.commit()
            return ApprovalClaim(False, reason="expired")
        if row["status"] != "pending":
            connection.rollback()
            return ApprovalClaim(False, reason="already_processed")

        connection.execute(
            "INSERT INTO resend_webhook_events (event_id, received_at) VALUES (?, ?)",
            (event_id, now),
        )
        connection.execute(
            "UPDATE email_approvals SET status = 'processing' WHERE token = ?",
            (token,),
        )
        connection.commit()
        return ApprovalClaim(True, thread_id=row["thread_id"])
    finally:
        connection.close()


def complete_approval(token: str, status: str) -> None:
    with _connection() as connection:
        connection.execute(
            """
            UPDATE email_approvals
            SET status = ?, completed_at = ?
            WHERE token = ?
            """,
            (status, int(time.time()), token),
        )


init_approval_db()
