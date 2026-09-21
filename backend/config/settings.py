import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    # -----------------------
    # APP CONFIG
    # -----------------------
    APP_NAME = "RAG MCP App"
    DEBUG = True

    # -----------------------
    # OPENAI
    # -----------------------
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

    # -----------------------
    # PINECONE
    # -----------------------
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINECONE_ENV")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "rag-index")

    # -----------------------
    # AWS S3
    # -----------------------
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    AWS_BUCKET = os.getenv("AWS_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

    # -----------------------
    # DATABASE
    # -----------------------
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

    # -----------------------
    # REDIS (for query caching)
    # -----------------------
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    CACHE_TTL_QUERIES = int(os.getenv("CACHE_TTL_QUERIES", 3600))  # 1 hour

    # -----------------------
    # RESEND MCP (email PDF summaries)
    # -----------------------
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RESEND_MCP_URL = os.getenv("RESEND_MCP_URL", "http://127.0.0.1:3000/mcp")
    SUMMARY_RECIPIENT_EMAIL = os.getenv("SUMMARY_RECIPIENT_EMAIL")
    SUMMARY_SENDER_EMAIL = os.getenv("SUMMARY_SENDER_EMAIL")
    SUMMARY_REPLY_TO_EMAIL = os.getenv("SUMMARY_REPLY_TO_EMAIL")
    APPROVAL_EMAIL = os.getenv("APPROVAL_EMAIL") or SUMMARY_RECIPIENT_EMAIL
    RESEND_RECEIVING_ADDRESS = os.getenv("RESEND_RECEIVING_ADDRESS")
    RESEND_RECEIVING_API_KEY = os.getenv("RESEND_RECEIVING_API_KEY")
    RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET")
    APPROVAL_TOKEN_TTL_SECONDS = int(os.getenv("APPROVAL_TOKEN_TTL_SECONDS", 3600))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")

    # -----------------------
    # EXTERNAL TOOLS
    # -----------------------
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


    # -----------------------
    # SECURITY
    # -----------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # -----------------------
    # VALIDATION CHECK (VERY IMPORTANT)
    # -----------------------
    def validate(self):
        missing = []

        required_vars = [
            "OPENAI_API_KEY",
            "PINECONE_API_KEY",
            "AWS_ACCESS_KEY",
            "AWS_SECRET_KEY",
            "AWS_BUCKET"
        ]

        for var in required_vars:
            if not getattr(self, var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing env variables: {missing}")


# Create instance
settings = Settings()

# Validate at startup
settings.validate()
