from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from routes import upload, chat, session, email, email_approval, resend_webhook

from db.database import init_db
init_db()   # run once at startup


app = FastAPI(
    title="RAG MCP Backend",
    version="1.0.0"
)

# -----------------------------
# CORS (allows browser clients hosted separately during development)
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

# ----------------------------------
# Routes
# ---------------------------------
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(email.router)
app.include_router(resend_webhook.router)
app.include_router(email_approval.router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get('/')
def home():
    return FileResponse(frontend_dir / "index.html")
