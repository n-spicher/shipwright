from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database.database import engine, get_db
from app.models import user as models
from app.models.document import Document
from app.models.keyword import Keyword
from app.schemas import user as schemas
from app.schemas.document import DocumentCreate, Document as DocumentSchema
from app.schemas.keyword import KeywordCreate, Keyword as KeywordSchema
from app.schemas.keyword_extraction import KeywordExtractionOutput
from app.utils.security import get_password_hash
from app.chains.chat import create_chat_chain
from app.chains.keyword_extraction import create_keyword_extraction_chain
from app.utils.pdf_processor import process_pdf
from pydantic import BaseModel
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import chromadb
import os
from dotenv import load_dotenv
from enum import Enum
import json
import logging
from datetime import datetime, timedelta
from time import sleep
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from app.utils.helpers import get_collection_name, find_applicable_keywords
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)
Document.__table__.create(bind=engine, checkfirst=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB client with new configuration
chroma_client = chromadb.PersistentClient(path="./data/chroma")

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=10000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# Initialize embeddings with Google's model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

class ChatMode(str, Enum):
    NONE = "NONE"
    GC = "GC"
    MC = "MC"
    EC = "EC"


def get_prompt_framing(mode: ChatMode) -> str:
    base_framing = "You are a friendly assistant named Shipwright tasked with answering questions about a document. Answer the question based only on the provided context."
    
    if mode == ChatMode.NONE:
        return base_framing
    elif mode == ChatMode.GC:
        return """You are Shipwright, an AI assistant specialized in construction document analysis for General Contractors (GCs). 
        Focus on overall project scope, scheduling, coordination between trades, and general construction requirements. 
        Answer the question based only on the provided context, emphasizing aspects relevant to GC responsibilities."""
    elif mode == ChatMode.MC:
        return """You are Shipwright, an AI assistant specialized in construction document analysis for Mechanical Contractors (MCs). 
        Focus on HVAC systems, mechanical equipment, ductwork, piping, and mechanical specifications. 
        Answer the question based only on the provided context, emphasizing mechanical systems and related requirements."""
    elif mode == ChatMode.EC:
        return """You are Shipwright, an AI assistant specialized in construction document analysis for Electrical Contractors (ECs). 
        Focus on electrical systems, power distribution, lighting, controls, and electrical specifications. 
        Answer the question based only on the provided context, emphasizing electrical systems and related requirements."""
    return base_framing


class ChatRequest(BaseModel):
    message: str
    user_id: int
    mode: ChatMode = ChatMode.NONE

class PDFUploadRequest(BaseModel):
    user_id: int

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user with email already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username is taken
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/ask")
async def ask(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # Verify user exists
        user = db.query(models.User).filter(models.User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get user keywords from database
        user_keywords = db.query(Keyword).filter(Keyword.user_id == request.user_id).all()
        
        # Find applicable keywords in the message using helper function
        applicable_keywords = find_applicable_keywords(request.message, user_keywords)

        # Get relevant chunks from ChromaDB using user-specific collection
        collection_name = get_collection_name(request.user_id)
        collection = chroma_client.get_collection(collection_name)
        
        # Start with semantic search using the original query
        query_embedding = embeddings.embed_query(request.message)
        semantic_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        # Extract results from semantic search
        chunks = semantic_results['documents'][0]
        metadatas = semantic_results['metadatas'][0]
        distances = semantic_results['distances'][0]
        
        # If we have applicable keywords, enhance the results
        if applicable_keywords:
            # Create a combined query using the original query and keywords
            combined_query = request.message
            keyword_terms = [kw.term for kw in applicable_keywords]
            
            # For each applicable keyword, do an additional search
            all_chunks = []
            all_metadatas = []
            all_distances = []
            seen_ids = set()  # Keep track of chunks we've already seen
            
            # First prioritize keyword-specific searches
            for keyword in applicable_keywords:
                # Create a query that combines the user query with the keyword example text
                keyword_query = f"{request.message} {keyword.example_text}"
                keyword_embedding = embeddings.embed_query(keyword_query)
                
                # Get results based on the keyword-enhanced query
                # Use more results for keywords since we're prioritizing them
                keyword_results = collection.query(
                    query_embeddings=[keyword_embedding],
                    n_results=3
                )
                
                # Add unique results
                for i, chunk in enumerate(keyword_results['documents'][0]):
                    chunk_id = keyword_results['ids'][0][i]
                    if chunk_id not in seen_ids:
                        all_chunks.append(chunk)
                        all_metadatas.append(keyword_results['metadatas'][0][i])
                        all_distances.append(keyword_results['distances'][0][i])
                        seen_ids.add(chunk_id)
            
            # Then add semantic search results that weren't already included
            for i, chunk in enumerate(chunks):
                chunk_id = semantic_results['ids'][0][i]
                if chunk_id not in seen_ids:
                    all_chunks.append(chunk)
                    all_metadatas.append(metadatas[i])
                    all_distances.append(distances[i])
                    seen_ids.add(chunk_id)
            
            # Update the chunks and metadata with the enhanced results
            chunks = all_chunks
            metadatas = all_metadatas
        
        # Combine relevant chunks into context
        context = "\n\n".join(chunks)
        
        # Create chat chain
        chain = create_chat_chain()
        
        # Prepare prompt with context and include applicable keywords if any
        prompt = f"""
            {get_prompt_framing(request.mode)}

                <context>
                {context}
                </context>

                <question>
                {request.message}
                </question>
        """
        
        # Add keyword section if applicable keywords were found
        if applicable_keywords:
            keyword_section = "\n\nAdditional instructions for specific keywords:\n"
            for keyword in applicable_keywords:
                keyword_section += f"- {keyword.term}: {keyword.example_text}\n"
            
            prompt += keyword_section
            
        response = chain.invoke(prompt)
        
        # Create response with applicable keywords
        return {
            "response": response,
            "chunks": [
                {
                    "text": chunk,
                    "metadata": metadata
                }
                for chunk, metadata in zip(chunks, metadatas)
            ],
            "applicable_keywords": [
                {
                    "id": keyword.id,
                    "term": keyword.term,
                    "example_text": keyword.example_text
                }
                for keyword in applicable_keywords
            ]
        }
    except Exception as e:
        logger.error(f"Error in ask: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def process_chunks_with_updates(chunks, document, collection, embeddings, rate_limiter):
    logger.info(f"Starting processing of {len(chunks)} chunks for document: {document.filename}")
    total_chunks = len(chunks)
    processed = 0
    update_frequency = 50

    try:
        for i, chunk_data in enumerate(chunks):
            try:
                logger.debug(f"Processing chunk {i}/{total_chunks} from page {chunk_data['page']}")
                
                logger.debug("Waiting for rate limiter...")
                rate_limiter.wait_if_needed()
                
                logger.debug(f"Generating embedding for chunk {i}")
                embedding = embeddings.embed_query(chunk_data['text'])
                
                logger.debug(f"Adding chunk {i} to ChromaDB collection")
                collection.add(
                    embeddings=[embedding],
                    documents=[chunk_data['text']],
                    ids=[f"doc_{document.id}_{i}"],
                    metadatas=[{
                        "document_id": document.id,
                        "filename": document.filename,
                        "page": chunk_data['page'],
                        "chunk_index": i
                    }]
                )
                
                processed += 1
                if processed % update_frequency == 0 or processed == total_chunks:
                    progress = {
                        "status": "processing",
                        "processed": processed,
                        "total": total_chunks,
                        "percentage": round((processed / total_chunks) * 100, 2)
                    }
                    logger.info(f"Progress update: {progress['percentage']}% complete")
                    yield json.dumps(progress) + "\n"
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {str(e)}", exc_info=True)
                error_msg = {
                    "status": "error",
                    "message": str(e),
                    "processed": processed,
                    "total": total_chunks
                }
                yield json.dumps(error_msg) + "\n"
                raise

        logger.info(f"Successfully completed processing all {total_chunks} chunks")
        yield json.dumps({
            "status": "complete",
            "processed": total_chunks,
            "total": total_chunks,
            "percentage": 100,
            "document_id": document.id
        }) + "\n"

    except Exception as e:
        logger.error(f"Fatal error in process_chunks_with_updates: {str(e)}", exc_info=True)
        raise

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF file with streaming progress updates
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Read the file content
        file_content = await file.read()
        
        # Create document record in database
        document = Document(
            user_id=user_id,
            filename=file.filename
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        async def generate():
            try:
                async for progress in process_pdf(file_content, file.filename, user_id):
                    # Add document_id to progress updates
                    progress["document_id"] = document.id
                    yield json.dumps(progress) + "\n"
                    
                    # If we encounter an error, stop processing
                    if progress.get("status") == "error":
                        # Delete the document from database if processing failed
                        db.delete(document)
                        db.commit()
                        break
                        
            except Exception as e:
                logger.error(f"Error in generate: {str(e)}")
                error_response = {
                    "status": "error",
                    "error": str(e),
                    "document_id": document.id
                }
                yield json.dumps(error_response) + "\n"
                # Delete the document from database if processing failed
                db.delete(document)
                db.commit()
        
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

@app.get("/chat_modes")
async def chat_modes():
    return [mode.value for mode in ChatMode]

@app.get("/documents/{user_id}", response_model=list[DocumentSchema])
def list_documents(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all documents for the user
    documents = db.query(Document).filter(Document.user_id == user_id).all()
    return documents

@app.post("/keywords/", response_model=KeywordSchema)
def create_keyword(keyword: KeywordCreate, user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_keyword = Keyword(**keyword.dict(), user_id=user_id)
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

@app.get("/keywords/{user_id}", response_model=list[KeywordSchema])
def read_keywords(user_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    keywords = db.query(Keyword).filter(Keyword.user_id == user_id).all()
    return keywords

@app.get("/keywords/{user_id}/{keyword_id}", response_model=KeywordSchema)
def read_keyword(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == user_id
    ).first()
    if keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return keyword

@app.put("/keywords/{user_id}/{keyword_id}", response_model=KeywordSchema)
def update_keyword(
    user_id: int,
    keyword_id: int,
    keyword: KeywordCreate,
    db: Session = Depends(get_db)
):
    db_keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == user_id
    ).first()
    if db_keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
    for key, value in keyword.dict().items():
        setattr(db_keyword, key, value)
    
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

@app.delete("/keywords/{user_id}/{keyword_id}")
def delete_keyword(user_id: int, keyword_id: int, db: Session = Depends(get_db)):
    db_keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == user_id
    ).first()
    if db_keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
    db.delete(db_keyword)
    db.commit()
    return {"message": "Keyword deleted successfully"}

@app.post("/keyword-upload")
async def keyword_upload(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    request_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    logger.info(f"[{request_id}] Starting keyword upload process for user_id: {user_id}, file: {file.filename}")
    
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            logger.error(f"[{request_id}] Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Check if user exists
        logger.info(f"[{request_id}] Checking if user exists: {user_id}")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            logger.error(f"[{request_id}] User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"[{request_id}] User found: {user.username}")
        
        # Read PDF content
        logger.info(f"[{request_id}] Starting PDF content extraction")
        try:
            pdf_reader = PyPDF2.PdfReader(file.file)
            document_content = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    document_content += text + "\n"
                    logger.debug(f"[{request_id}] Extracted text from page {page_num}")
                except Exception as page_error:
                    logger.error(f"[{request_id}] Error extracting text from page {page_num}: {str(page_error)}")
                    continue
            
        except Exception as pdf_error:
            logger.error(f"[{request_id}] Error reading PDF: {str(pdf_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error reading PDF file")
        
        # Create keyword extraction chain
        logger.info(f"[{request_id}] Creating keyword extraction chain")
        
        chain_executor = create_keyword_extraction_chain()
        
        # Extract keywords from document
        logger.info(f"[{request_id}] Starting keyword extraction from document")
        try:
            # Create a clean input dictionary with only what's needed
            chain_input = {"document_content": document_content}
            logger.info(f"[{request_id}] Input keys: {list(chain_input.keys())}")
            
            try:
                result = chain_executor(chain_input)
                logger.info(f"[{request_id}] Extracted {len(result.keywords)} keywords")
                for idx, keyword in enumerate(result.keywords, 1):
                    logger.debug(f"[{request_id}] Keyword {idx}: term='{keyword.term}', example_text='{keyword.example_text}'")
            except ValueError as value_error:
                error_msg = str(value_error)
                logger.error(f"[{request_id}] ValueError during chain invocation: {error_msg}")
                
                # Check for specific missing key errors
                if "Missing some input keys" in error_msg:
                    logger.error(f"[{request_id}] Input validation failed - provided keys: {list(chain_input.keys())}")
                    
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error during keyword extraction: {error_msg}"
                )
        except Exception as chain_invoke_error:
            logger.error(f"[{request_id}] Error during chain invocation: {str(chain_invoke_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error during keyword extraction")
        
        # Save keywords to database
        logger.info(f"[{request_id}] Starting database operations")
        try:
            created_keywords = []
            for idx, keyword in enumerate(result.keywords, 1):
                try:
                    logger.debug(f"[{request_id}] Creating database record for keyword {idx}")
                    db_keyword = Keyword(
                        user_id=user_id,
                        term=keyword.term,
                        example_text=keyword.example_text
                    )
                    db.add(db_keyword)
                    created_keywords.append(db_keyword)
                    logger.debug(f"[{request_id}] Added keyword {idx}/{len(result.keywords)} to session")
                except Exception as keyword_error:
                    logger.error(f"[{request_id}] Error creating keyword {idx}: {str(keyword_error)}", exc_info=True)
                    continue
            
            logger.info(f"[{request_id}] Committing {len(created_keywords)} keywords to database")
            db.commit()
            
            # Refresh all created keywords to get their IDs
            for idx, keyword in enumerate(created_keywords, 1):
                try:
                    db.refresh(keyword)
                    logger.debug(f"[{request_id}] Refreshed keyword {idx}/{len(created_keywords)}")
                except Exception as refresh_error:
                    logger.error(f"[{request_id}] Error refreshing keyword {idx}: {str(refresh_error)}", exc_info=True)
            
            logger.info(f"[{request_id}] Successfully completed keyword upload process")
            return {
                "message": f"Successfully extracted and saved {len(created_keywords)} keywords",
                "keywords": [KeywordSchema.from_orm(k) for k in created_keywords]
            }
            
        except Exception as db_error:
            logger.error(f"[{request_id}] Database operation error: {str(db_error)}", exc_info=True)
            db.rollback()
            raise HTTPException(status_code=500, detail="Error saving keywords to database")
            
    except HTTPException as http_error:
        logger.error(f"[{request_id}] HTTP error: {str(http_error)}")
        raise http_error
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            file.file.close()
            logger.info(f"[{request_id}] Closed file handle")
        except Exception as close_error:
            logger.error(f"[{request_id}] Error closing file: {str(close_error)}", exc_info=True)

class RateLimiter:
    def __init__(self, max_requests_per_minute):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < timedelta(minutes=1)]
        
        if len(self.requests) >= self.max_requests:
            # Wait until the oldest request is more than 1 minute old
            sleep_time = 61 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.2f} seconds")
                sleep(sleep_time)
            self.requests = self.requests[1:]
        
        self.requests.append(now)

@app.delete("/documents/{user_id}/{document_id}")
async def delete_document(user_id: int, document_id: str, db: Session = Depends(get_db)):
    """
    Delete a document and its associated vector embeddings
    
    Args:
        user_id: ID of the user who owns the document
        document_id: ID of the document to delete
        db: Database session
    
    Returns:
        dict: Success message
    """
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if document exists and belongs to user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document from ChromaDB
        try:
            collection_name = get_collection_name(user_id)
            collection = chroma_client.get_collection(collection_name)
            # Delete all chunks associated with this document
            collection.delete(
                where={"document_id": document_id}
            )
            logger.info(f"Deleted document {document_id} from ChromaDB collection {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting document from ChromaDB: {str(e)}")
            # Continue with database deletion even if ChromaDB deletion fails
        
        # Delete document from database
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/all-documents/{user_id}")
async def delete_all_user_documents(user_id: int, db: Session = Depends(get_db)):
    """
    Delete all documents and their associated vector embeddings for a user
    
    Args:
        user_id: ID of the user whose documents should be deleted
        db: Database session
    
    Returns:
        dict: Success message with count of deleted documents
    """
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all documents for the user
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        document_count = len(documents)
        
        # Delete documents from ChromaDB
        try:
            collection_name = get_collection_name(user_id)
            # Delete the entire collection
            chroma_client.delete_collection(collection_name)
            logger.info(f"Deleted ChromaDB collection {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting ChromaDB collection: {str(e)}")
            # Continue with database deletion even if ChromaDB deletion fails
        
        # Delete all documents from database
        for document in documents:
            db.delete(document)
        db.commit()
        
        return {
            "message": f"Successfully deleted {document_count} documents and associated vector embeddings",
            "deleted_count": document_count
        }
        
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Error deleting all documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,  # override deafult port
        reload=True,
        reload_dirs=["app"]  # Only watch the app directory for changes
    ) 