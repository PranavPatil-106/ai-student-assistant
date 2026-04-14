import os
import boto3
import uuid
import tempfile
from typing import Optional, Dict, List
from datetime import datetime
from db import WorkspaceItem, User
from dotenv import load_dotenv

load_dotenv()

class FileService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            endpoint_url=os.getenv("AWS_ENDPOINT_URL")
        )
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        if not self.bucket_name:
            print("Warning: AWS_S3_BUCKET is not set. Storage might fail if called.")

    def save_file(self, owner_id: int, subject: str, unit: str, filename: str, file_content: bytes, replace: bool, db_session) -> WorkspaceItem:
        if replace:
            # Delete existing in DB and S3
            existing_items = db_session.query(WorkspaceItem).filter(
                WorkspaceItem.owner_id == owner_id,
                WorkspaceItem.subject == subject,
                WorkspaceItem.unit == unit
            ).all()
            for item in existing_items:
                if self.bucket_name:
                    try:
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=item.s3_key)
                    except Exception:
                        pass
                db_session.delete(item)
            db_session.commit()
            
        # Generate S3 key
        s3_key = f"user_{owner_id}/{subject}/{unit}/{uuid.uuid4()}_{filename}"
        
        # Upload to S3
        if self.bucket_name:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=s3_key, Body=file_content)
            
        # Save to DB
        pinecone_ns = f"user-{owner_id}-{subject}-{unit}".replace(" ", "-").lower()
        # Pinecone namespace must be alphanumeric, dashes only for safety
        pinecone_ns = "".join([c if c.isalnum() else "-" for c in pinecone_ns])

        new_item = WorkspaceItem(
            owner_id=owner_id,
            subject=subject,
            unit=unit,
            filename=filename,
            s3_key=s3_key,
            pinecone_namespace=pinecone_ns,
            embedding_done=False
        )
        db_session.add(new_item)
        db_session.commit()
        db_session.refresh(new_item)
        return new_item

    def get_file_content(self, s3_key: str) -> bytes:
        if not self.bucket_name:
            return b""
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
        return response['Body'].read()

    def download_to_temp(self, s3_key: str, filename: str) -> str:
        """Download to temp file for text extractor"""
        if not self.bucket_name:
            raise Exception("S3 Bucket not configured")
        
        ext = os.path.splitext(filename)[1]
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        content = self.get_file_content(s3_key)
        with open(temp_file.name, 'wb') as f:
            f.write(content)
        return temp_file.name

    def load_metadata(self, owner_id: int, subject: str, unit: str, db_session) -> Dict:
        items = db_session.query(WorkspaceItem).filter(
            WorkspaceItem.owner_id == owner_id,
            WorkspaceItem.subject == subject,
            WorkspaceItem.unit == unit
        ).all()
        
        documents = []
        embedding_done = False
        if items:
            embedding_done = all(item.embedding_done for item in items)
            for item in items:
                documents.append({
                    "id": item.id,
                    "filename": item.filename,
                    "uploaded_at": item.uploaded_at.isoformat(),
                    "s3_key": item.s3_key
                })
                
        return {
            "subject": subject,
            "unit": unit,
            "embedding_done": embedding_done,
            "documents": documents
        }
    
    def mark_embedding_done(self, owner_id: int, subject: str, unit: str, db_session):
        items = db_session.query(WorkspaceItem).filter(
            WorkspaceItem.owner_id == owner_id,
            WorkspaceItem.subject == subject,
            WorkspaceItem.unit == unit
        ).all()
        for item in items:
            item.embedding_done = True
        db_session.commit()

    def get_all_documents(self, owner_id: int, subject: str, unit: str, db_session) -> List[WorkspaceItem]:
        return db_session.query(WorkspaceItem).filter(
            WorkspaceItem.owner_id == owner_id,
            WorkspaceItem.subject == subject,
            WorkspaceItem.unit == unit
        ).all()

    def get_all_subjects(self, owner_id: int, db_session) -> List[str]:
        subjects = db_session.query(WorkspaceItem.subject).filter(
            WorkspaceItem.owner_id == owner_id
        ).distinct().all()
        return [s[0] for s in subjects]
        
    def get_units_for_subject(self, owner_id: int, subject: str, db_session) -> List[str]:
        units = db_session.query(WorkspaceItem.unit).filter(
            WorkspaceItem.owner_id == owner_id,
            WorkspaceItem.subject == subject
        ).distinct().all()
        return [u[0] for u in units]

    def is_embedding_done(self, owner_id: int, subject: str, unit: str, db_session) -> bool:
        items = db_session.query(WorkspaceItem).filter(
            WorkspaceItem.owner_id == owner_id,
            WorkspaceItem.subject == subject,
            WorkspaceItem.unit == unit
        ).all()
        if not items:
            return False
        return all(item.embedding_done for item in items)

_file_service_instance = None

def get_file_service() -> FileService:
    global _file_service_instance
    if _file_service_instance is None:
        _file_service_instance = FileService()
    return _file_service_instance
