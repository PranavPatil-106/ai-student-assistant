from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from services.file_service import get_file_service
from services.rag_service import get_rag_service
from api.auth import get_current_user
from db import get_db, User, WorkspaceItem

router = APIRouter()

class SummaryRequest(BaseModel):
    subject: str
    unit: str
    owner_id: int
    chapter: Optional[str] = None

class MCQRequest(BaseModel):
    subject: str
    unit: str
    owner_id: int
    count: int = 10
    previous_questions: Optional[List[str]] = None

class FlashcardRequest(BaseModel):
    subject: str
    unit: str
    owner_id: int
    count: int = 10
    previous_cards: Optional[List[str]] = None

class AskRequest(BaseModel):
    subject: str
    unit: str
    owner_id: int
    question: str

def verify_student_access(student: User, owner_id: int, db: Session):
    if student.id == owner_id:
        return True
        
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner or owner.role != 'faculty':
        raise HTTPException(status_code=403, detail="Forbidden access to this workspace.")
        
    if owner.college != student.college or owner.branch != student.branch:
        raise HTTPException(status_code=403, detail="You can only access faculty materials from your own college and branch.")
    return True

@router.post("/summary")
async def generate_summary(
    request: SummaryRequest,
    llm_provider: str = Header(...),
    llm_api_key: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_student_access(current_user, request.owner_id, db)
    file_service = get_file_service()
    if not file_service.is_embedding_done(request.owner_id, request.subject, request.unit, db):
        raise HTTPException(status_code=400, detail="Materials not processed yet.")
        
    rag_service = get_rag_service()
    try:
        return rag_service.generate_summary(request.owner_id, request.subject, request.unit, llm_provider, llm_api_key, request.chapter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mcq")
async def generate_mcq(
    request: MCQRequest,
    llm_provider: str = Header(...),
    llm_api_key: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_student_access(current_user, request.owner_id, db)
    file_service = get_file_service()
    if not file_service.is_embedding_done(request.owner_id, request.subject, request.unit, db):
        raise HTTPException(status_code=400, detail="Materials not processed yet.")
        
    rag_service = get_rag_service()
    try:
        return rag_service.generate_mcqs(request.owner_id, request.subject, request.unit, llm_provider, llm_api_key, request.count, request.previous_questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/flashcards")
async def generate_flashcards(
    request: FlashcardRequest,
    llm_provider: str = Header(...),
    llm_api_key: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_student_access(current_user, request.owner_id, db)
    file_service = get_file_service()
    if not file_service.is_embedding_done(request.owner_id, request.subject, request.unit, db):
        raise HTTPException(status_code=400, detail="Materials not processed yet.")
        
    rag_service = get_rag_service()
    try:
        return rag_service.generate_flashcards(request.owner_id, request.subject, request.unit, llm_provider, llm_api_key, request.count, request.previous_cards)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_question(
    request: AskRequest,
    llm_provider: str = Header(...),
    llm_api_key: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_student_access(current_user, request.owner_id, db)
    file_service = get_file_service()
    if not file_service.is_embedding_done(request.owner_id, request.subject, request.unit, db):
        raise HTTPException(status_code=400, detail="Materials not processed yet.")
        
    rag_service = get_rag_service()
    try:
        return rag_service.ask_question(request.owner_id, request.subject, request.unit, request.question, llm_provider, llm_api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspaces")
async def get_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Returns available workspaces: own subjects + faculty subjects in the same college/branch
    file_service = get_file_service()
    
    # Own subjects
    own_subjects = file_service.get_all_subjects(current_user.id, db)
    result = [{"owner_id": current_user.id, "type": "Personal", "subjects": own_subjects}]
    
    # Faculty subjects matching criteria
    faculty = db.query(User).filter(
        User.role == 'faculty',
        User.college == current_user.college,
        User.branch == current_user.branch,
        # Potentially year_of_study matching, or just branch
    ).all()
    
    for f in faculty:
        f_subjects = file_service.get_all_subjects(f.id, db)
        if f_subjects:
            result.append({
                "owner_id": f.id,
                "owner_name": f.full_name,
                "type": "Faculty",
                "subjects": f_subjects
            })
            
    return {"workspaces": result}

@router.get("/units/{owner_id}/{subject}")
async def get_units(owner_id: int, subject: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verify_student_access(current_user, owner_id, db)
    file_service = get_file_service()
    units = file_service.get_units_for_subject(owner_id, subject, db)
    return {"subject": subject, "owner_id": owner_id, "units": units}
