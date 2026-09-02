from pinecone import Pinecone, ServerlessSpec
from config.settings import settings


def init_pinecone():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    index_name = settings.PINECONE_INDEX

    # Check if index exists
    existing_indexes = [i["name"] for i in pc.list_indexes()]

    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI embedding size
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"   
            )
        )

    return pc


def get_index():
    pc = init_pinecone()
    return pc.Index(settings.PINECONE_INDEX)