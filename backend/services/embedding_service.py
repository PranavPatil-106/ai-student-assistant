import os
from typing import List, Dict, Optional
from utils.text_extractor import extract_text, chunk_text
from utils.hf_embeddings import get_embeddings
from services.file_service import get_file_service
import uuid
from pinecone import Pinecone
from db import WorkspaceItem
from dotenv import load_dotenv

load_dotenv()

class EmbeddingService:
    def __init__(self):
        pc_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX", "student-assistant-index")
        
        if pc_key:
            self.pc = Pinecone(api_key=pc_key)
            self.index = self.pc.Index(self.index_name)
        else:
            print("Warning: PINECONE_API_KEY is not set.")
            self.pc = None
            self.index = None

    def get_namespace(self, owner_id: int, subject: str, unit: str) -> str:
        ns = f"user-{owner_id}-{subject}-{unit}".replace(" ", "-").lower()
        return "".join([c if c.isalnum() else "-" for c in ns])
    
    def process_and_embed_documents(self, owner_id: int, subject: str, unit: str, db_session) -> Dict:
        file_service = get_file_service()
        
        documents = file_service.get_all_documents(owner_id, subject, unit, db_session)
        if not documents:
            return {
                "status": "error",
                "message": "No documents found for this subject/unit"
            }
            
        embeddings = get_embeddings()
        namespace = self.get_namespace(owner_id, subject, unit)
        
        total_chunks = 0
        processed_files = []
        
        for doc in documents:
            temp_path = None
            try:
                # Download file to temp to extract text
                temp_path = file_service.download_to_temp(doc.s3_key, doc.filename)
                text = extract_text(temp_path)
                
                if not text:
                    continue
                
                chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
                if not chunks:
                    continue
                
                chunk_embeddings = embeddings.embed_documents(chunks)
                
                # Pinecone upsert limit is usually 100-200 vectors at a time
                vectors = []
                for i in range(len(chunks)):
                    # Store chunk text in metadata
                    metadata = {
                        "source": doc.filename,
                        "subject": subject,
                        "unit": unit,
                        "chunk_index": i,
                        "text": chunks[i] # Store text directly in vector metadata
                    }
                    vectors.append({
                        "id": str(uuid.uuid4()),
                        "values": chunk_embeddings[i],
                        "metadata": metadata
                    })
                
                # Batch upsert
                batch_size = 100
                if self.index:
                    for i in range(0, len(vectors), batch_size):
                        self.index.upsert(
                            vectors=vectors[i:i+batch_size],
                            namespace=namespace
                        )
                
                total_chunks += len(chunks)
                processed_files.append({
                    "file": doc.filename,
                    "chunks": len(chunks)
                })
                
            except Exception as e:
                print(f"Error processing {doc.filename}: {str(e)}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
        
        file_service.mark_embedding_done(owner_id, subject, unit, db_session)
        
        return {
            "status": "success",
            "subject": subject,
            "unit": unit,
            "total_chunks": total_chunks,
            "processed_files": processed_files,
            "namespace": namespace
        }
    
    def query_documents(self, owner_id: int, subject: str, unit: str, query: str, n_results: int = 5) -> List[Dict]:
        if not self.index:
            return []
            
        embeddings = get_embeddings()
        namespace = self.get_namespace(owner_id, subject, unit)
        
        query_embedding = embeddings.embed_query(query)
        
        results = self.index.query(
            namespace=namespace,
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True
        )
        
        formatted_results = []
        if results and getattr(results, 'matches', None):
            for match in results.matches:
                formatted_results.append({
                    "content": match.metadata.get("text", ""),
                    "metadata": match.metadata,
                    "distance": match.score
                })
                
        return formatted_results
    
    def get_all_documents_content(self, owner_id: int, subject: str, unit: str) -> str:
        # Pinecone doesn't support fetching ALL vectors in a namespace easily without knowing IDs.
        # But we can query with a dummy vector and high top_k, OR use 'fetch' if we stored IDs.
        # A simpler way since it's a student app is to do a dummy query covering the space.
        # But we actually want ALL text for flashcards/summary.
        # Better approach: query Pinecone with top_k=10000 and dummy vector [0] * dim?
        # Alternatively, we can query Pinecone using metadata filtering if it's supported.
        # Actually, for summarization/flashcards over entire unit, extracting from vectors is flawed! 
        # But keeping it similar to previous logic:
        if not self.index:
            return ""
            
        namespace = self.get_namespace(owner_id, subject, unit)
        dim = get_embeddings().get_embedding_dimension()
        dummy_vector = [0.0] * dim
        
        # We query for up to 1000 vectors
        results = self.index.query(
            namespace=namespace,
            vector=dummy_vector,
            top_k=1000,
            include_metadata=True
        )
        
        content = []
        if results and getattr(results, 'matches', None):
            for match in results.matches:
                text = match.metadata.get("text", "")
                if text:
                    content.append(text)
                    
        return "\\n\\n".join(content)

_embedding_service_instance = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
