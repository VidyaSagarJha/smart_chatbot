from fastapi import APIRouter
from pydantic import BaseModel
from services.qa_service import get_answer, is_contextual_followup
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
    # 1. Load history before checking the cache. Follow-up questions such as
    # "tell me more" only have meaning within their conversation.
    history = get_history(req.session_id)

    # 2. Build the same bounded context used for answering and cache identity.
    history_text = ""
    for msg in history[-5:]:
        history_text += f"{msg['role']}: {msg['content']}\n"

    # 3. Standalone questions share cached answers across sessions. Only
    # ambiguous follow-ups need conversation history in their cache identity.
    cache_context = history_text if is_contextual_followup(req.query) else ""
    cached_answer = cache_query_response(req.query, req.doc_id, cache_context)
    if cached_answer:
        logger.info(f"Cache hit! Using cached response for: {req.query[:50]}...")
        return {"answer": cached_answer, "from_cache": True}

    # 4. Generate an answer.
    answer = get_answer(req.query, req.doc_id, history_text)

    # 5. cache the response
    set_query_cache(req.query, req.doc_id, answer, cache_context)

    # 6. save to DB
    save_message(req.session_id, "user", req.query)
    save_message(req.session_id, "assistant", answer)

    return {"answer": answer, "from_cache": False}
