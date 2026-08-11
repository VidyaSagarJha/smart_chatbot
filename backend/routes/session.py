from fastapi import APIRouter
import uuid

router = APIRouter()

@router.get("/session")
def create_session():
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}