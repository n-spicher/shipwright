import os
import tempfile
import logging
from typing import Optional, AsyncGenerator, Dict, Any
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
import io
import chromadb
import json
import asyncio
from datetime import datetime, timedelta
from asyncio import Lock
from app.utils.helpers import get_collection_name
# Get logger
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_ENABLED = True  # Set to False to disable rate limiting
REQUESTS_PER_MINUTE = 140  # Keep slightly under the 150 limit for safety
REQUEST_WINDOW = 60  # seconds

# Rate limiting state
request_timestamps = []
last_request_time = None
rate_limit_lock = Lock()

async def wait_for_rate_limit():
    """
    Rate limiting function that ensures we don't exceed the API limits.
    Can be disabled by setting RATE_LIMIT_ENABLED to False.
    """
    if not RATE_LIMIT_ENABLED:
        return
        
    global request_timestamps, last_request_time
    
    async with rate_limit_lock:
        current_time = datetime.now()
        
        # Remove timestamps older than the window
        request_timestamps = [ts for ts in request_timestamps 
                            if current_time - ts < timedelta(seconds=REQUEST_WINDOW)]
        
        # If we've hit the limit, wait until we can make another request
        if len(request_timestamps) >= REQUESTS_PER_MINUTE:
            wait_time = (request_timestamps[0] + timedelta(seconds=REQUEST_WINDOW) - current_time).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
        
        # Add current request timestamp
        request_timestamps.append(current_time)
        last_request_time = current_time

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./data/chroma")

# Initialize embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using PyPDF2 and add page break markers
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        str: Extracted text content with page break markers
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text_content = ""
            
            for page in reader.pages:
                text_content += page.extract_text()
            
            return text_content.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

async def process_pdf(file_content: bytes, filename: str, user_id: int) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process a PDF file and create embeddings for chunks of text.
    Yields progress updates during processing.
    """
    try:
        # Create user-specific collection
        collection_name = get_collection_name(user_id)
        collection = chroma_client.get_or_create_collection(collection_name)
        
        # Read PDF and extract all text with page numbers
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)
        
        # Extract all text from PDF with page numbers
        all_text = ""
        page_texts = []
        for page_num, page in enumerate(pdf_reader.pages, 1):
            page_text = page.extract_text()
            page_texts.append((page_num, page_text))
            all_text += page_text + "\n"
        
        # Split text into chunks of 10000 characters
        chunk_size = 5000
        chunks = [all_text[i:i + chunk_size] for i in range(0, len(all_text), chunk_size)]
        total_chunks = len(chunks)
        
        yield {
            "status": "started",
            "total_chunks": total_chunks,
            "message": f"Starting to process {total_chunks} chunks"
        }
        
        # Process each chunk
        processed_chunks = 0
        skipped_chunks = 0
        
        for chunk_num, chunk in enumerate(chunks, 1):
            try:
                # Skip empty chunks or chunks with very little content
                if not chunk or len(chunk.strip()) < 10:
                    skipped_chunks += 1
                    yield {
                        "status": "skipped",
                        "current_chunk": chunk_num,
                        "total_chunks": total_chunks,
                        "percentage": round((chunk_num / total_chunks) * 100, 2),
                        "message": f"Skipped empty chunk {chunk_num}"
                    }
                    continue
                
                # Find which pages this chunk contains
                chunk_start = (chunk_num - 1) * chunk_size
                chunk_end = chunk_start + len(chunk)
                current_pos = 0
                chunk_pages = []
                
                for page_num, page_text in page_texts:
                    page_start = current_pos
                    page_end = current_pos + len(page_text)
                    
                    # Check if this chunk overlaps with this page
                    if (chunk_start < page_end and chunk_end > page_start):
                        chunk_pages.append(page_num)
                    
                    current_pos += len(page_text) + 1  # +1 for the newline we added
                
                # Wait for rate limit before making API call
                await wait_for_rate_limit()
                
                # Generate embedding
                try:
                    embedding = embeddings.embed_query(chunk)
                except Exception as e:
                    if "429" in str(e):  # Rate limit error
                        logger.warning("Rate limit hit, waiting and retrying...")
                        await asyncio.sleep(60)  # Wait a minute
                        await wait_for_rate_limit()  # Wait for our rate limiter
                        embedding = embeddings.embed_query(chunk)
                    else:
                        raise
                
                # Add to ChromaDB with page numbers in metadata
                collection.add(
                    embeddings=[embedding],
                    documents=[chunk],
                    ids=[f"doc_{filename}_chunk_{chunk_num}"],
                    metadatas=[{
                        "filename": filename,
                        "chunk": chunk_num,
                        "user_id": user_id,
                        "pages": chunk_pages
                    }]
                )
                
                processed_chunks += 1
                
                # Yield progress update
                yield {
                    "status": "processing",
                    "current_chunk": chunk_num,
                    "total_chunks": total_chunks,
                    "percentage": round((chunk_num / total_chunks) * 100, 2),
                    "message": f"Processed chunk {chunk_num} of {total_chunks}"
                }
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {str(e)}")
                yield {
                    "status": "error",
                    "current_chunk": chunk_num,
                    "total_chunks": total_chunks,
                    "error": str(e)
                }
                continue
        
        yield {
            "status": "complete",
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "skipped_chunks": skipped_chunks,
            "percentage": 100,
            "message": f"PDF processing completed. Processed {processed_chunks} chunks, skipped {skipped_chunks} empty chunks."
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        yield {
            "status": "error",
            "error": str(e)
        }
