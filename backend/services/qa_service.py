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
    page_terms = ("page", "pages")
    count_terms = ("how many", "number", "no.", "total", "count")
    return any(term in normalized for term in page_terms) and any(
        term in normalized for term in count_terms
    )


def is_summary_request(query: str) -> bool:
    return bool(re.search(
        r"\b(summarize|summary|summery|overview|gist)\b",
        query.lower(),
    ))


def is_contextual_followup(query: str) -> bool:
    """Detect short questions whose subject comes from conversation history."""
    normalized = re.sub(r"[^a-z0-9\s]", "", query.lower()).strip()
    return normalized in {
        "tell me more", "more", "explain more", "elaborate", "continue",
        "what else", "and", "why", "how so", "about him", "about her",
        "about them", "what about him", "what about her", "what about them",
    }


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
    # Validate metadata
    if not metadata or "chunk_count" not in metadata:
        return "Document metadata not found."
    
    chunks = retrieve_document_chunks(doc_id, metadata["chunk_count"])
    if not chunks:
        return "I couldn't retrieve this document's text for summarization."

    sentence_count, was_capped = requested_sentence_count(query)
    llm = get_llm()
    partial_summaries = []

    try:
        for start in range(0, len(chunks), SUMMARY_BATCH_SIZE):
            section = "\n\n".join(chunks[start:start + SUMMARY_BATCH_SIZE])
            
            # Skip empty sections
            if not section.strip():
                continue
            
            response = llm.invoke(f"""
Summarize this section of a document faithfully. Preserve key facts, names,
dates, responsibilities, numbers, and conclusions. Do not add information
that is not present in the text.

Section:
{section}
""")
            partial_summaries.append(response.content)

        # Check if we got any summaries
        if not partial_summaries:
            return "Could not summarize document - all sections were empty."

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
    
    except Exception as e:
        return f"Error generating summary: {str(e)}"

BLOCKED_TERMS = [
    # Prompt-injection attempts
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "reveal your system prompt",
    "show your system prompt",
    "print your instructions",
    "bypass safety",
    "bypass guardrails",
    "jailbreak",

    # Harmful requests
    "hack",
    "kill",
    "bomb",
    "suicide",
    "jailbreak",
    "password"

    # Sensitive-data requests
    "show api key",
    "reveal api key",
    "show password",
    "reveal password",
    "credit card number",
    
]

def is_blocked_query(query:str) -> str:
    normalized = query.lower().strip()
    return any(term in normalized for term in BLOCKED_TERMS)

def get_answer(query: str, doc_id: str, history_text: str = ""):
    if is_blocked_query(query):
        return "This query cannot be processed"


    if is_greeting(query):
        return "Hello! What would you like to know about your PDFs?"

    metadata = get_document_metadata(doc_id)
    if is_page_count_question(query) and metadata:
        page_count = metadata["page_count"]
        return f"This PDF collection has {page_count} page{'s' if page_count != 1 else ''} in total."

    if is_summary_request(query) and metadata:
        return summarize_document(query, doc_id, metadata)

    # Resolve vague follow-ups using recent conversation context. Without this,
    # an embedding for "tell me more" can retrieve an unrelated PDF/person.
    retrieval_query = query
    if history_text and is_contextual_followup(query):
        retrieval_query = f"{history_text[-2000:]}\nFollow-up question: {query}"

    chunks = retrieve_chunks(retrieval_query, doc_id)
    context = "\n\n".join(chunks)

    llm = get_llm()

    prompt = f"""
You are a helpful assistant answering questions about a collection of PDFs.
Answer only from the given context. The source PDF labels are trustworthy
metadata and may be used to identify which document the user means. For broad
requests such as "tell me about X", give a useful overview of what the retrieved
passages establish about X. If the context does not contain enough relevant
information, say "I don't know". Answer in the same language as the question.

Context:
{context}

Conversation so far:
{history_text}

Current question:
{query}

Answer:
"""
    print(f"📨 Prompt being sent: {prompt}")   

    response = llm.invoke(prompt)

    print(f"✅ LLM response: {response.content}") 

    return response.content
