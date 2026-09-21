from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from agents.agent_service import get_document_agent_status, run_document_agent
from services.memory_service import save_message, get_history

router = APIRouter()

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    doc_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    document_name: str = Field(default="uploaded documents", max_length=500)


@router.post("/chat")
async def chat(req: ChatRequest):
    history = get_history(req.session_id)
    try:
        response = await run_in_threadpool(
            run_document_agent,
            query=req.query,
            doc_id=req.doc_id,
            session_id=req.session_id,
            document_name=req.document_name,
            history=history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="The document agent could not complete this request.") from exc

    save_message(req.session_id, "user", req.query)
    save_message(req.session_id, "assistant", response["answer"])

    return response


@router.get("/chat/status/{session_id}")
async def chat_status(session_id: str):
    return await run_in_threadpool(get_document_agent_status, session_id)
