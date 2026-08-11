from langchain_openai import OpenAIEmbeddings
from config.settings import settings

def get_embeddings():
    return OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY,
        chunk_size=100
    )
