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
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keyword_upload.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)
Document.__table__.create(bind=engine, checkfirst=True)

app = FastAPI()

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
    chunk_size=1000,
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
    document_id: str
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
        # Verify document exists
        document = db.query(Document).filter(Document.id == request.document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get relevant chunks from ChromaDB
        collection = chroma_client.get_collection("pdf_documents")
        query_embedding = embeddings.embed_query(request.message)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"document_id": request.document_id}
        )

        # Get the chunks and their metadata
        chunks = results['documents'][0]
        metadatas = results['metadatas'][0]

        # Combine relevant chunks into context
        context = "\n\n".join(chunks)
        
        # Create chat chain
        chain = create_chat_chain()
        
        # Prepare prompt with context
        prompt = f"""
            {get_prompt_framing(request.mode)}

                Context:
                {context}

                Question: {request.message}
            """

        response = chain.invoke(prompt)
        return {
            "response": response,
            "chunks": [
                {
                    "text": chunk,
                    "metadata": metadata
                }
                for chunk, metadata in zip(chunks, metadatas)
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-pdf", response_model=DocumentSchema)
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Create document record
        document = Document(
            user_id=user_id,
            filename=file.filename
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Read PDF content with page tracking
        pdf_reader = PyPDF2.PdfReader(file.file)
        page_texts = []
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text()
            if text.strip():  # Only add non-empty pages
                page_texts.append({
                    'text': text,
                    'page': page_num
                })
        
        # Split text into chunks while preserving page information
        chunks = []
        for page_data in page_texts:
            page_chunks = text_splitter.split_text(page_data['text'])
            for chunk in page_chunks:
                chunks.append({
                    'text': chunk,
                    'page': page_data['page']
                })
        
        # Create or get collection
        collection = chroma_client.get_or_create_collection(
            name="pdf_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Generate embeddings and add to ChromaDB
        for i, chunk_data in enumerate(chunks):
            embedding = embeddings.embed_query(chunk_data['text'])
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
        
        return document
    
    except Exception as e:
        # If there's an error, delete the document record
        if 'document' in locals():
            db.delete(document)
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()

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
            
            logger.info(f"[{request_id}] Successfully extracted text from {len(pdf_reader.pages)} pages")
            logger.debug(f"[{request_id}] Document content length: {len(document_content)} characters")
            logger.debug(f"[{request_id}] First 500 characters of content: {document_content[:500]}")
        except Exception as pdf_error:
            logger.error(f"[{request_id}] Error reading PDF: {str(pdf_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error reading PDF file")
        
        # Create keyword extraction chain
        logger.info(f"[{request_id}] Creating keyword extraction chain")
        try:
            chain = create_keyword_extraction_chain()
            logger.info(f"[{request_id}] Successfully created keyword extraction chain")
        except Exception as chain_error:
            logger.error(f"[{request_id}] Error creating keyword extraction chain: {str(chain_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error initializing keyword extraction")
        
        # Extract keywords from document
        logger.info(f"[{request_id}] Starting keyword extraction from document")
        try:
            logger.debug(f"[{request_id}] Invoking chain with document content")
            result = chain.invoke({"document_content": document_content})
            logger.info(f"[{request_id}] Successfully received response from chain")
            logger.debug(f"[{request_id}] Chain response type: {type(result)}")
            logger.debug(f"[{request_id}] Chain response: {result}")
            
            if not hasattr(result, 'keywords'):
                logger.error(f"[{request_id}] Chain response missing 'keywords' attribute")
                logger.error(f"[{request_id}] Response attributes: {dir(result)}")
                raise ValueError("Chain response missing 'keywords' attribute")
                
            logger.info(f"[{request_id}] Extracted {len(result.keywords)} keywords")
            for idx, keyword in enumerate(result.keywords, 1):
                logger.debug(f"[{request_id}] Keyword {idx}: term='{keyword.term}', example_text='{keyword.example_text}'")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        reload_dirs=["app"]  # Only watch the app directory for changes
    ) 