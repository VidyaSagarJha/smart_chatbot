from fastapi import APIRouter
from pydantic import BaseModel
from services.qa_service import get_answer
from services.memory_service import save_message, get_history

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    doc_id: str
    session_id: str   


@router.post("/chat")
def chat(req: ChatRequest):
    # 1. get history from DB
    history = get_history(req.session_id)

    # 2. build context
    history_text = ""
    for msg in history[-5:]:
        history_text += f"{msg['role']}: {msg['content']}\n"

    enhanced_query = f"""
            Conversation so far: {history_text}
            Current question: {req.query}
                """

    # 3. get answer
    answer = get_answer(req.query, req.doc_id, history_text)

    # 4. save to DB
    save_message(req.session_id, "user", req.query)
    save_message(req.session_id, "assistant", answer)

    return {"answer": answer}           