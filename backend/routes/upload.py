from fastapi import APIRouter, UploadFile, File
from services.s3_service import upload_file
from services.rag_pipeline import process_pdf

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # upload to S3
    file_url = upload_file(file.file)

    if not file_url:                          # ✅ check S3 succeeded
        return {"error": "S3 upload failed"}

    # process into vector DB
    chunks = process_pdf(file_url)

    return {
        "message": "Upload + RAG complete ✅",
        "file_url": file_url,
        "chunks_created": chunks["chunks"],  # ✅ updated
        "doc_id": chunks["doc_id"]           # ✅ added
    }