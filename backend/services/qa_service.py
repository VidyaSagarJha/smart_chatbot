from langchain_openai import ChatOpenAI
from services.retriever import retrieve_chunks, retrieve_document_chunks
from services.memory_service import get_document_metadata
from config.settings import settings
import re

MAX_SUMMARY_SENTENCES = 50
SUMMARY_BATCH_SIZE = 10


def is_greeting(query: str) -> bool:
    """Return True for a short, standalone greeting."""
    normalized = re.sub(r"[^a-z\s]", "", query.lower()).strip()
    greetings = {
        "hi", "hello", "hey", "greetings", "good morning",
        "good afternoon", "good evening",
    }
    return normalized in greetings


def is_page_count_question(query: str) -> bool:
    normalized = query.lower()
    return bool(re.search(r"(how many|number of|total) pages?|page count", normalized))


def is_summary_request(query: str) -> bool:
    return bool(re.search(r"\b(summarize|summary|overview|gist)\b", query.lower()))


def requested_sentence_count(query: str) -> tuple[int, bool]:
    match = re.search(r"\b(\d+)\s+sentences?\b", query.lower())
    requested = int(match.group(1)) if match else 10
    return min(requested, MAX_SUMMARY_SENTENCES), requested > MAX_SUMMARY_SENTENCES


def get_llm():
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0,
    )


def summarize_document(query: str, doc_id: str, metadata: dict):
    chunks = retrieve_document_chunks(doc_id, metadata["chunk_count"])
    if not chunks:
        return "I couldn't retrieve this document's text for summarization."

    sentence_count, was_capped = requested_sentence_count(query)
    llm = get_llm()
    partial_summaries = []

    for start in range(0, len(chunks), SUMMARY_BATCH_SIZE):
        section = "\n\n".join(chunks[start:start + SUMMARY_BATCH_SIZE])
        response = llm.invoke(f"""
Summarize this section of a document faithfully. Preserve key facts, names,
dates, responsibilities, numbers, and conclusions. Do not add information
that is not present in the text.

Section:
{section}
""")
        partial_summaries.append(response.content)

    combined_summaries = "\n\n".join(partial_summaries)
    response = llm.invoke(f"""
Create a clear, faithful summary of the full document using only the section
summaries below. Use at most {sentence_count} sentences. Do not invent facts.

Section summaries:
{combined_summaries}
""")

    cap_notice = ""
    if was_capped:
        cap_notice = f"You requested more than {MAX_SUMMARY_SENTENCES} sentences, so the summary is capped at {MAX_SUMMARY_SENTENCES}.\n\n"
    return cap_notice + response.content


def get_answer(query: str, doc_id: str, history_text: str = ""):
    if is_greeting(query):
        return "Hello! What would you like to know about your PDF?"

    metadata = get_document_metadata(doc_id)
    if is_page_count_question(query) and metadata:
        page_count = metadata["page_count"]
        return f"This PDF has {page_count} page{'s' if page_count != 1 else ''}."

    if is_summary_request(query) and metadata:
        return summarize_document(query, doc_id, metadata)

    # 1. Retrieve using ONLY the clean query
    chunks = retrieve_chunks(query, doc_id)
    context = "\n\n".join(chunks)

    llm = get_llm()

    prompt = f"""
You are a helpful assistant.
Answer ONLY from the given context.
If answer is not in context, say "I don't know".

Context:
{context}

Conversation so far:
{history_text}

Current question:
{query}

Answer:
"""
    print(f"📨 Prompt being sent: {prompt}")    # ✅ add

    response = llm.invoke(prompt)

    print(f"✅ LLM response: {response.content}") # ✅ add

    return response.content
