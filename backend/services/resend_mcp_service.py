"""Client for the official Resend MCP server over Streamable HTTP."""

import html
import logging
from typing import Any

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from config.settings import settings

logger = logging.getLogger(__name__)


class ResendMCPError(RuntimeError):
    """A safe-to-display error produced while calling the email MCP server."""


def _configuration_error() -> str | None:
    required = {
        "RESEND_API_KEY": settings.RESEND_API_KEY,
        "SUMMARY_RECIPIENT_EMAIL": settings.SUMMARY_RECIPIENT_EMAIL,
        "SUMMARY_SENDER_EMAIL": settings.SUMMARY_SENDER_EMAIL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        return "Missing email configuration: " + ", ".join(missing)
    return None


def _result_text(result: Any) -> str:
    """Return human-readable text from an MCP CallToolResult."""
    parts = []
    for item in getattr(result, "content", []) or []:
        value = getattr(item, "text", None)
        if value:
            parts.append(value)
    return "\n".join(parts)


async def send_email(
    subject: str,
    content: str,
    recipient: str | None = None,
    reply_to: str | None = None,
    html_content: str | None = None,
) -> str:
    """Send approved content through Resend's MCP `send-email` tool."""
    configuration_error = _configuration_error()
    if configuration_error:
        raise ResendMCPError(configuration_error)

    safe_subject = subject.strip() or "Document assistant message"
    text = content.strip()
    body_html = html_content or (
        f"<h2>{html.escape(safe_subject)}</h2>"
        f"<pre style=\"font-family:Arial,sans-serif;white-space:pre-wrap\">"
        f"{html.escape(text)}</pre>"
    )
    arguments = {
        "from": settings.SUMMARY_SENDER_EMAIL,
        "replyTo": [
            reply_to or settings.SUMMARY_REPLY_TO_EMAIL or settings.SUMMARY_SENDER_EMAIL
        ],
        "to": [recipient or settings.SUMMARY_RECIPIENT_EMAIL],
        "subject": safe_subject,
        "text": text,
        "html": body_html,
    }
    headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}
    try:
        async with httpx2.AsyncClient(headers=headers, timeout=60.0) as http_client:
            async with streamable_http_client(
                settings.RESEND_MCP_URL,
                http_client=http_client,
            ) as streams:
                # MCP SDK releases return either (read, write) or
                # (read, write, get_session_id); only the first two are needed.
                read_stream, write_stream = streams[:2]
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool("send-email", arguments)
    except Exception as exc:
        logger.exception("Resend MCP request failed")
        raise ResendMCPError(
            "Could not reach the Resend MCP server. Check that it is running and configured."
        ) from exc

    if getattr(result, "isError", False) or getattr(result, "is_error", False):
        logger.error("Resend MCP returned an error: %s", _result_text(result))
        raise ResendMCPError("Resend could not send the email. Check its server logs.")

    return _result_text(result) or "Email sent successfully."


async def send_summary_email(summary: str, document_name: str = "your PDF") -> str:
    """Backward-compatible summary-email wrapper used by the REST endpoint."""
    safe_document_name = document_name.strip() or "your PDF"
    return await send_email(
        subject=f"Summary: {safe_document_name}",
        content=f"PDF summary for {safe_document_name}\n\n{summary}",
    )
