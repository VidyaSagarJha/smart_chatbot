from typing import Literal, TypedDict


RouteName = Literal[
    "question_answer",
    "summary",
    "analysis",
    "comparison",
    "email_last_answer",
]


class DocumentAgentState(TypedDict, total=False):
    query: str
    doc_id: str
    session_id: str
    history_text: str
    document_name: str
    last_answer: str

    route: RouteName
    requires_email: bool
    result: str

    email_subject: str
    email_body: str
    approval_token: str
    approval_status: str
    final_answer: str
    error: str
