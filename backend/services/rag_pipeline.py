from utils.pdf_loader import load_pdf_from_url
from utils.chunking import split_documents
from services.embeddings import get_embeddings
from services.pinecone_service import init_pinecone
from services.memory_service import save_document_metadata
from config.settings import settings
import uuid


def process_pdfs(files: list[dict[str, str]]):
    """Index several PDFs as one searchable document collection."""
    docs = []
    page_count = 0

    for file_number, item in enumerate(files):
        file_docs = load_pdf_from_url(item["url"])
        page_count += len(file_docs)
        for document in file_docs:
            document.metadata.update({
                "source": item["url"],
                "file_name": item["name"],
                "file_number": file_number,
            })
        docs.extend(file_docs)

    print(f"Loaded {page_count} pages from {len(files)} PDFs")

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

    for i, (chunk, vector) in enumerate(zip(chunks, vectors_values)):
        vectors.append({
            "id": f"{doc_id}-{i}",
            "values": vector,
            "metadata": {
                "text": chunk.page_content,
                "source": chunk.metadata.get("source", ""),
                "file_name": chunk.metadata.get("file_name", ""),
                "page": chunk.metadata.get("page", 0),
                "doc_id": doc_id,
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
        "chunks": len(chunks),
        "pages": page_count,
        "files": len(files),
        "doc_id": doc_id,
    }


def process_pdf(file_url: str):
    """Backward-compatible wrapper for callers that index one PDF."""
    return process_pdfs([{"url": file_url, "name": "document.pdf"}])
