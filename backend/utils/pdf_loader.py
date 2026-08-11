import requests
import os
from tempfile import NamedTemporaryFile
from langchain_community.document_loaders import PyPDFLoader  # ✅ fixed import

def load_pdf_from_url(url: str):
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch PDF from S3: {response.status_code}")

    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()
    finally:
        os.remove(tmp_path)

    return documents