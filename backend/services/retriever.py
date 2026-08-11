from services.pinecone_service import get_index
from services.embeddings import get_embeddings


def retrieve_chunks(query: str, doc_id: str, top_k: int = 3):
    index = get_index()
    embeddings = get_embeddings()

    query_vector = embeddings.embed_query(query)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter={"doc_id": doc_id}
    )

    print(f"🔍 Searching for doc_id: {doc_id}")          # ✅ add this
    print(f"📦 Pinecone results: {results}")              # ✅ add this
    print(f"📄 Matches found: {len(results['matches'])}") # ✅ add this

    chunks = [
        match["metadata"]["text"]
        for match in results["matches"]
    ]

    return chunks


def retrieve_document_chunks(doc_id: str, chunk_count: int, batch_size: int = 100):
    """Fetch every chunk belonging to one document in its original order."""
    index = get_index()
    chunk_ids = [f"{doc_id}-{number}" for number in range(chunk_count)]
    chunks = []

    for start in range(0, len(chunk_ids), batch_size):
        batch_ids = chunk_ids[start:start + batch_size]
        response = index.fetch(ids=batch_ids)
        vectors = response.get("vectors", {})

        for vector_id in batch_ids:
            vector = vectors.get(vector_id)
            if vector:
                chunks.append(vector["metadata"]["text"])

    return chunks
