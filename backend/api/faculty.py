from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
from services.file_service import get_file_service
from services.embedding_service import get_embedding_service
from services.rag_service import get_rag_service
from api.auth import get_current_user
from db import get_db, User

router = APIRouter()

class UploadResponse(BaseModel):
    status: str
    message: str
    subject: str
    unit: str
    filename: str

class StatusResponse(BaseModel):
    status: str
    subject: str
    unit: str
    embedding_done: bool
    documents: List[dict]

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    subject: str = Form(...),
    unit: str = Form(...),
    file: UploadFile = File(...),
    replace: str = Form("false"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != 'faculty':
         raise HTTPException(status_code=403, detail="Only faculty can upload materials to this endpoint.")
         
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    try:
        file_content = await file.read()
        file_service = get_file_service()
        replace_mode = replace.lower() == "true"
        file_service.save_file(current_user.id, subject, unit, file.filename, file_content, replace_mode, db)
        
        if background_tasks:
            embedding_service = get_embedding_service()
            background_tasks.add_task(
                embedding_service.process_and_embed_documents,
                current_user.id,
                subject,
                unit,
                db
            )
            message = "File uploaded successfully. Embeddings are generating."
        else:
            message = "File uploaded successfully. Embeddings will be generated."
        
        return UploadResponse(
            status="success", message=message, subject=subject, unit=unit, filename=file.filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")

@router.get("/status", response_model=StatusResponse)
async def get_status(subject: str, unit: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_service = get_file_service()
    try:
        metadata = file_service.load_metadata(current_user.id, subject, unit, db)
        return StatusResponse(
            status="success", subject=subject, unit=unit,
            embedding_done=metadata.get("embedding_done", False),
            documents=metadata.get("documents", [])
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")

@router.post("/generate-embeddings")
async def generate_embeddings(
    subject: str = Form(...),
    unit: str = Form(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    embedding_service = get_embedding_service()
    try:
        if background_tasks:
            background_tasks.add_task(
                embedding_service.process_and_embed_documents, current_user.id, subject, unit, db
            )
            return {"status": "processing", "message": "Embedding background started"}
        else:
            return embedding_service.process_and_embed_documents(current_user.id, subject, unit, db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")

@router.post("/generate-content")
async def generate_content(
    subject: str = Form(...),
    unit: str = Form(...),
    content_type: str = Form(...),
    llm_provider: str = Header(...),
    llm_api_key: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_service = get_file_service()
    if not file_service.is_embedding_done(current_user.id, subject, unit, db):
        raise HTTPException(status_code=400, detail="Please generate embeddings first")
    
    rag_service = get_rag_service()
    try:
        if content_type == "summary":
            result = rag_service.generate_summary(current_user.id, subject, unit, llm_provider, llm_api_key)
        elif content_type == "mcq":
            result = rag_service.generate_mcqs(current_user.id, subject, unit, llm_provider, llm_api_key, count=10)
        elif content_type == "flashcards":
            result = rag_service.generate_flashcards(current_user.id, subject, unit, llm_provider, llm_api_key, count=10)
        else:
            raise HTTPException(status_code=400, detail="Invalid content_type")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/subjects")
async def get_subjects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_service = get_file_service()
    subjects = file_service.get_all_subjects(current_user.id, db)
    return {"subjects": subjects}

@router.get("/units/{subject}")
async def get_units(subject: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_service = get_file_service()
    units = file_service.get_units_for_subject(current_user.id, subject, db)
    return {"subject": subject, "units": units}
