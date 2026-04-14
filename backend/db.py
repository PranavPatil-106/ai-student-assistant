from sqlalchemy import create_engine, Column, Integer, String, Enum, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MySQL connection settings
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "student_assistant")

# We add ssl_cert options if user switches to TiDB / Aiven in Production
# Example: ?ssl_verify_cert=true&ssl_verify_identity=true
ssl_args = {}
# TiDB / remote DB often require SSL. This can be configured in the connection string.
DATABASE_URL = os.getenv("DATABASE_URL", f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")

# Create engine
engine = create_engine(DATABASE_URL, echo=False, connect_args=ssl_args)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('student', 'faculty'), nullable=False)
    
    # Multi-tenancy fields
    college = Column(String(200), nullable=True)
    branch = Column(String(100), nullable=True)
    year_of_study = Column(String(20), nullable=True) # E.g., '1st Year', '2nd Year', '3rd Year', '4th Year'
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class WorkspaceItem(Base):
    __tablename__ = "workspace_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(100), nullable=False)
    unit = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False, unique=True)
    pinecone_namespace = Column(String(200), nullable=False) # Store the namespace for vectors
    embedding_done = Column(Boolean, default=False)
    uploaded_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    owner = relationship("User")

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
