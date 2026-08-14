import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from services.memory_service import get_document_metadata
from services.qa_service import summarize_document
from services.resend_mcp_service import ResendMCPError, send_summary_email

logger = logging.getLogger(__name__)
router = APIRouter()


class EmailSummaryRequest(BaseModel):
    doc_id: str = Field(min_length=1)
    document_name: str = Field(default="your PDF", max_length=255)


@router.post("/email-summary")
async def email_summary(req: EmailSummaryRequest):
    """Create a document summary and deliver it using the Resend MCP tool."""
    metadata = get_document_metadata(req.doc_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document metadata not found.")

    summary = await run_in_threadpool(
        summarize_document,
        "Summarize this document in 10 sentences.",
        req.doc_id,
        metadata,
    )
    if summary.startswith(
        (
            "Document metadata not found",
            "I couldn't retrieve",
            "Could not summarize",
            "Error generating",
        )
    ):
        raise HTTPException(status_code=500, detail="Could not generate a summary for this document.")

    try:
        confirmation = await send_summary_email(summary, req.document_name)
    except ResendMCPError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    logger.info("Sent document summary using the Resend MCP server")
    return {"message": "Summary email sent.", "confirmation": confirmation}
