from fastapi import APIRouter
from pydantic import BaseModel
from services.qa_service import get_answer
from services.memory_service import save_message, get_history
from services.cache_service import cache_query_response, set_query_cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    doc_id: str
    session_id: str   


@router.post("/chat")
def chat(req: ChatRequest):
    # 1. Check cache first
    cached_answer = cache_query_response(req.query, req.doc_id)
    if cached_answer:
        logger.info(f"Cache hit! Using cached response for: {req.query[:50]}...")
        return {"answer": cached_answer, "from_cache": True}
    
    # 2. get history from DB
    history = get_history(req.session_id)

    # 3. build context
    history_text = ""
    for msg in history[-5:]:
        history_text += f"{msg['role']}: {msg['content']}\n"

    # 4. get answer
    answer = get_answer(req.query, req.doc_id, history_text)

    # 5. cache the response
    set_query_cache(req.query, req.doc_id, answer)

    # 6. save to DB
    save_message(req.session_id, "user", req.query)
    save_message(req.session_id, "assistant", answer)

    return {"answer": answer, "from_cache": False}
