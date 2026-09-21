import html
import secrets

from fastapi import APIRouter, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

from agents.agent_service import resume_document_agent_from_email
from config.settings import settings
from services.approval_service import claim_approval, complete_approval


router = APIRouter()


def _page(title: str, content: str) -> HTMLResponse:
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
          <head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
          <body style="margin:0;background:#f4f7fb;font-family:Arial,sans-serif;color:#172033">
            <main style="max-width:620px;margin:60px auto;background:white;padding:32px;border-radius:16px;border:1px solid #e3e8f1">
              <h1 style="margin-top:0">{html.escape(title)}</h1>
              {content}
            </main>
          </body>
        </html>
        """
    )


@router.get("/approvals/email/{token}", response_class=HTMLResponse)
def review_email_action(token: str, decision: str | None = None):
    safe_token = html.escape(token, quote=True)
    if decision in {"approve", "reject"}:
        label = "Approve and send" if decision == "approve" else "Reject email"
        color = "#157347" if decision == "approve" else "#bd2e44"
        return _page(
            f"Confirm {decision}",
            f"""
            <p>Please confirm this email action.</p>
            <form method="post" action="/approvals/email/{safe_token}">
              <input type="hidden" name="decision" value="{decision}">
              <button type="submit" style="border:0;border-radius:8px;padding:12px 18px;background:{color};color:white;font-weight:bold;cursor:pointer">{label}</button>
            </form>
            """,
        )
    return _page(
        "Review email action",
        f"""
        <p>Choose whether the document-agent email should be sent.</p>
        <form method="post" action="/approvals/email/{safe_token}" style="display:inline-block;margin-right:10px">
          <input type="hidden" name="decision" value="approve">
          <button type="submit" style="border:0;border-radius:8px;padding:12px 18px;background:#157347;color:white;font-weight:bold;cursor:pointer">Approve and send</button>
        </form>
        <form method="post" action="/approvals/email/{safe_token}" style="display:inline-block">
          <input type="hidden" name="decision" value="reject">
          <button type="submit" style="border:0;border-radius:8px;padding:12px 18px;background:#bd2e44;color:white;font-weight:bold;cursor:pointer">Reject</button>
        </form>
        """,
    )


@router.post("/approvals/email/{token}", response_class=HTMLResponse)
async def process_email_action(token: str, decision: str = Form()):
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Invalid approval decision.")

    claim = claim_approval(
        token=token,
        sender_email=settings.APPROVAL_EMAIL or "",
        event_id=f"button:{token}:{secrets.token_urlsafe(8)}",
    )
    if not claim.accepted:
        return _page(
            "Approval unavailable",
            f"<p>This approval could not be processed: {html.escape(claim.reason)}.</p>",
        )

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
    title = "Email approved" if decision == "approve" else "Email rejected"
    return _page(title, f"<p>{html.escape(result['answer'])}</p>")
