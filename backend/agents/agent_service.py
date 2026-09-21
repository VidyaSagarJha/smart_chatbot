from typing import Any

from langgraph.types import Command

from agents.document_graph import document_graph
from services.qa_service import is_greeting


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _interrupt_payload(result: dict) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__", [])
    if not interrupts:
        return None
    value = getattr(interrupts[0], "value", None)
    return value if isinstance(value, dict) else {"message": str(value)}


def _approval_message(payload: dict[str, Any]) -> str:
    return (
        "An approval request was sent by email. The final email has not been sent.\n\n"
        f"Approver: {payload.get('approver', 'configured approver')}\n"
        f"Final subject: {payload.get('subject', '')}\n\n"
        "Reply APPROVE or REJECT to the approval email. This chat workflow will "
        "resume when Resend delivers the verified reply webhook."
    )


def _last_assistant_answer(history: list[dict]) -> str:
    for message in reversed(history):
        if message.get("role") == "assistant":
            return message.get("content", "")
    return ""


def run_document_agent(
    *,
    query: str,
    doc_id: str,
    session_id: str,
    document_name: str,
    history: list[dict],
) -> dict:
    """Start or resume one stateful LangGraph document-agent run."""
    config = _config(session_id)
    snapshot = document_graph.get_state(config)

    if snapshot.next:
        return {
            "answer": (
                "This workflow is waiting for an email reply from the configured "
                "approver. Reply APPROVE or REJECT to the approval email."
            ),
            "requires_approval": True,
            "agent": "communication",
        }
    if is_greeting(query):
        return {
            "answer": "Hello! What would you like to know about your PDFs?",
            "requires_approval": False,
            "agent": "direct",
        }
    else:
        history_text = "\n".join(
            f"{message['role']}: {message['content']}" for message in history[-8:]
        )
        result = document_graph.invoke(
            {
                "query": query,
                "doc_id": doc_id,
                "session_id": session_id,
                "document_name": document_name or "uploaded documents",
                "history_text": history_text,
                "last_answer": _last_assistant_answer(history),
                "requires_email": False,
                "result": "",
                "final_answer": "",
                "error": "",
            },
            config=config,
        )

    payload = _interrupt_payload(result)
    if payload:
        return {
            "answer": _approval_message(payload),
            "requires_approval": True,
            "agent": "communication",
        }

    return {
        "answer": result.get("final_answer") or result.get("result") or "Done.",
        "requires_approval": False,
        "agent": result.get("route", "router"),
    }


def resume_document_agent_from_email(*, thread_id: str, decision: str) -> dict:
    """Resume a paused email action after the inbound webhook is verified."""
    if decision not in {"approve", "reject"}:
        raise ValueError("Unsupported email approval decision.")
    config = _config(thread_id)
    snapshot = document_graph.get_state(config)
    if not snapshot.next:
        raise ValueError("This workflow is not waiting for approval.")

    result = document_graph.invoke(
        Command(resume={"action": decision}),
        config=config,
    )
    return {
        "answer": result.get("final_answer") or "Approval processed.",
        "requires_approval": False,
        "agent": "communication",
    }


def get_document_agent_status(session_id: str) -> dict:
    """Return the latest persisted status for frontend approval polling."""
    snapshot = document_graph.get_state(_config(session_id))
    if not snapshot.values:
        return {"status": "not_found"}
    if snapshot.next:
        return {"status": "pending"}

    approval_status = snapshot.values.get("approval_status")
    if approval_status == "completed":
        return {
            "status": "completed",
            "answer": snapshot.values.get("final_answer", "Email sent."),
        }
    if approval_status == "rejected":
        return {
            "status": "rejected",
            "answer": snapshot.values.get(
                "final_answer", "Email cancelled. Nothing was sent."
            ),
        }
    if snapshot.values.get("error"):
        return {
            "status": "failed",
            "answer": snapshot.values.get("final_answer", "The email action failed."),
        }
    return {"status": "idle"}
