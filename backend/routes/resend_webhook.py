import html
import json
import re
from email.utils import parseaddr

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from svix.webhooks import Webhook

from agents.agent_service import resume_document_agent_from_email
from config.settings import settings
from services.approval_service import claim_approval, complete_approval


router = APIRouter()
TOKEN_PATTERN = re.compile(r"\[APPROVAL:([A-Za-z0-9_-]+)\]", re.IGNORECASE)


async def _received_email(email_id: str) -> dict:
    if not settings.RESEND_RECEIVING_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Resend Receiving API key is not configured.",
        )
    headers = {"Authorization": f"Bearer {settings.RESEND_RECEIVING_API_KEY}"}
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        response = await client.get(
            f"https://api.resend.com/emails/receiving/{email_id}"
        )
        response.raise_for_status()
        return response.json()


def _decision_from_body(body: str) -> str | None:
    for line in body.splitlines():
        normalized = re.sub(r"[^a-z]", "", line.lower())
        if not normalized:
            continue
        if normalized in {"approve", "approved", "yes"}:
            return "approve"
        if normalized in {"reject", "rejected", "no", "cancel"}:
            return "reject"
        # Stop before quoted reply content such as "On ... wrote:".
        if line.lstrip().startswith((">", "On ")):
            break
    return None


@router.post("/webhooks/resend/inbound")
async def resend_inbound_webhook(request: Request):
    if not settings.RESEND_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Resend webhook is not configured.")

    raw_body = await request.body()
    webhook_headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    if not all(webhook_headers.values()):
        raise HTTPException(status_code=400, detail="Missing webhook signature headers.")

    try:
        payload = raw_body.decode("utf-8")
        Webhook(settings.RESEND_WEBHOOK_SECRET).verify(payload, webhook_headers)
        event = json.loads(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from exc

    if event.get("type") != "email.received":
        return {"status": "ignored"}

    event_data = event.get("data") or {}
    email_id = event_data.get("email_id")
    event_id = request.headers["svix-id"]
    if not email_id:
        raise HTTPException(status_code=400, detail="Missing received email ID.")

    try:
        email = await _received_email(email_id)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not retrieve received email.") from exc

    token_match = TOKEN_PATTERN.search(email.get("subject") or "")
    if not token_match:
        return {"status": "ignored", "reason": "approval_token_missing"}

    sender_email = parseaddr(email.get("from") or "")[1].lower()
    body = email.get("text") or re.sub(
        r"<[^>]+>", " ", html.unescape(email.get("html") or "")
    )
    decision = _decision_from_body(body)
    if not decision:
        return {"status": "ignored", "reason": "decision_missing"}

    token = token_match.group(1)
    claim = claim_approval(
        token=token,
        sender_email=sender_email,
        event_id=event_id,
    )
    if not claim.accepted:
        return {"status": "ignored", "reason": claim.reason}

    try:
        result = await run_in_threadpool(
            resume_document_agent_from_email,
            thread_id=claim.thread_id,
            decision=decision,
        )
    except Exception:
        complete_approval(token, "failed")
        raise

    complete_approval(token, "approved" if decision == "approve" else "rejected")
    return {"status": "processed", "decision": decision, "result": result["answer"]}
