from fastapi import APIRouter, UploadFile, File, HTTPException
from services.s3_service import upload_file
from services.rag_pipeline import process_pdfs

router = APIRouter()

@router.post("/upload")
async def upload_pdfs(
    files: list[UploadFile] | None = File(default=None),
    file: UploadFile | None = File(default=None),
):
    # Accept the old singular field as well, so cached clients do not fail with 422.
    selected_files = list(files or [])
    if file is not None:
        selected_files.append(file)

    if not selected_files:
        raise HTTPException(status_code=400, detail="Select at least one PDF.")

    invalid_files = [
        file.filename or "unnamed file"
        for file in selected_files
        if file.content_type != "application/pdf"
        and not (file.filename or "").lower().endswith(".pdf")
    ]
    if invalid_files:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are supported: {', '.join(invalid_files)}",
        )

    uploaded_files = []
    for file in selected_files:
        file_url = upload_file(file.file)
        if not file_url:
            raise HTTPException(
                status_code=502,
                detail=f"S3 upload failed for {file.filename or 'a PDF'}.",
            )
        uploaded_files.append({"url": file_url, "name": file.filename or "document.pdf"})

    result = process_pdfs(uploaded_files)

    return {
        "message": f"{len(selected_files)} PDF(s) uploaded and indexed.",
        "files": [{"name": item["name"], "url": item["url"]} for item in uploaded_files],
        "chunks_created": result["chunks"],
        "pages": result["pages"],
        "doc_id": result["doc_id"],
    }
