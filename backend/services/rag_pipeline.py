from utils.pdf_loader import load_pdf_from_url
from utils.chunking import split_documents
from services.embeddings import get_embeddings
from services.pinecone_service import init_pinecone
from services.memory_service import save_document_metadata
from config.settings import settings
import uuid


def process_pdf(file_url: str):
    # 1. Load PDF
    docs = load_pdf_from_url(file_url)
    print(f"Loaded {len(docs)} pages")
    page_count = len(docs)

    # 2. Chunk
    chunks = split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    # 3. Embeddings
    embeddings = get_embeddings()

    # 4. Init Pinecone
    pc = init_pinecone()
    index = pc.Index(settings.PINECONE_INDEX)

    # 🔥 unique document id
    doc_id = str(uuid.uuid4())

    # 5. Prepare vectors
    texts = [chunk.page_content for chunk in chunks]
    vectors_values = embeddings.embed_documents(texts)

    vectors = []

    for i, (text, vector) in enumerate(zip(texts, vectors_values)):
        vectors.append({
            "id": f"{doc_id}-{i}",
            "values": vector,
            "metadata": {
                "text": text,
                "source": file_url,
                "doc_id": doc_id
            }
        })

    # # 6. Upsert without batching
    #     index.upsert(vectors=vectors)

    # 6. Upsert in batches to support large documents
    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[start:start + batch_size])

    save_document_metadata(
        doc_id=doc_id,
        page_count=page_count,
        chunk_count=len(chunks),
    )

    return {
        "chunks": len(chunks),  # ✅ correct
        "doc_id": doc_id        # ✅ correct
    }
