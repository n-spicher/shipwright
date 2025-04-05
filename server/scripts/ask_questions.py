import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List
import httpx
from enum import Enum
import time
import random

# Add the parent directory to the Python path to allow importing from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# List of questions to ask
questions = [
    "What geologic formation underlies the project site, and how is it generally described?",
    "What are the primary risks associated with developing in karst terrain?",
    "How can construction activities such as blasting impact the development of solutioning features like sinkholes?",
    "What specific recommendations are made to reduce the risk of future sinkhole development during and after construction?",
    "What was discovered during the field exploration in terms of subsurface conditions, including the presence of groundwater and bedrock?",
    "What type and model of hydraulic elevators are specified for the project, and how many elevators are to be installed?",
    "What related sections in the contract documents should be coordinated with the hydraulic elevator work?",
    "What are the elevator car enclosure finish materials and dimensions specified in the project?",
    "What seismic design requirements must the elevator system comply with, and what is the project's Seismic Design Category?",
    "What standby power operation and energy-saving features are included in the elevator operation system?",
    "What components are included in the scope of the incandescent interior lighting section?",
    "Which specification sections are related to lighting controls and relay-based lighting control systems?",
    "What is the definition of a luminaire according to the document?",
    "What warranty period is specified for luminaires, and who is responsible for the warranty?",
    "What compliance standards must electrical components and luminaires meet, including UL and NFPA references?",
    "What requirements are specified for materials used in luminaires, such as sheet metal and factory-applied labels?",
    "What are the acceptable installation methods and support requirements for suspended lighting luminaires?",
    "What is required when using permanent luminaires for temporary lighting during construction?",
    "What are the identification requirements for electrical system components and connections in this section?",
    "What adjustments and services must be provided within 12 months of substantial completion?"
]

# Chat mode enum to match what's in the API
class ChatMode(str, Enum):
    NONE = "NONE"
    GC = "GC"
    MC = "MC"
    EC = "EC"

async def wait_with_backoff(retry_count=0, base_delay=1):
    """
    Wait with exponential backoff to handle rate limits
    
    Args:
        retry_count: Current retry count
        base_delay: Base delay in seconds
    """
    # Exponential backoff with jitter
    max_delay = min(60, base_delay * (2 ** retry_count))
    delay = random.uniform(base_delay, max_delay)
    logger.info(f"Rate limit exceeded. Waiting {delay:.2f} seconds before retry {retry_count + 1}...")
    await asyncio.sleep(delay)

async def ask_question_api(user_id: int, question: str, api_url: str, chat_mode: ChatMode = ChatMode.NONE, max_retries=5) -> Dict[str, Any]:
    """
    Ask a question via the API endpoint with retry logic for rate limits
    
    Args:
        user_id: ID of the user whose documents to query
        question: The question to ask
        api_url: The API URL to use
        chat_mode: The chat mode to use (NONE, GC, MC, EC)
        max_retries: Maximum number of retries for rate limit errors
        
    Returns:
        Dict with question, answer, and relevant chunks
    """
    retry_count = 0
    
    while True:
        try:
            # Prepare request to API
            payload = {
                "user_id": user_id,
                "message": question,
                "mode": chat_mode
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{api_url}/ask", json=payload)
                response.raise_for_status()
                result = response.json()
            
            # Format the response
            return {
                "question": question,
                "answer": result.get("response", "No response received"),
                "chunks": result.get("chunks", [])
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and retry_count < max_retries:
                # Rate limit error, retry with backoff
                retry_count += 1
                await wait_with_backoff(retry_count)
            else:
                logger.error(f"HTTP error asking question via API: {e}")
                return {
                    "question": question,
                    "answer": f"Error: {str(e)}",
                    "chunks": []
                }
        except Exception as e:
            logger.error(f"Error asking question via API: {str(e)}", exc_info=True)
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "chunks": []
            }

async def main():
    parser = argparse.ArgumentParser(description="Ask a series of questions via API without evaluation")
    parser.add_argument("user_id", type=int, help="User ID to query documents for")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="API URL (default: http://localhost:8000)")
    parser.add_argument("--output", "-o", type=str, help="Output file for results (JSON format)")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit number of questions (default: all)")
    parser.add_argument("--mode", "-m", type=str, choices=["NONE", "GC", "MC", "EC"], default="NONE", 
                        help="Chat mode (default: NONE)")
    parser.add_argument("--delay", "-d", type=float, default=10.0, 
                        help="Delay between questions in seconds (default: 10.0)")
    parser.add_argument("--max-per-minute", type=int, default=5,
                        help="Maximum requests per minute to stay under API limits (default: 5)")
    parser.add_argument("--report", "-r", type=str, help="Text report file path (e.g. report.txt)", default="report.txt")
    
    args = parser.parse_args()
    
    user_id = args.user_id
    api_url = args.api_url
    chat_mode = ChatMode(args.mode)
    limit = args.limit if args.limit is not None else len(questions)
    questions_to_ask = questions[:limit]
    delay_between_questions = args.delay
    max_per_minute = args.max_per_minute
    report_path = args.report
    
    # Calculate minimum delay to respect max_per_minute
    min_delay_for_rate_limit = 60.0 / max_per_minute
    if delay_between_questions < min_delay_for_rate_limit:
        logger.warning(f"Increasing delay to {min_delay_for_rate_limit:.2f}s to respect max {max_per_minute} requests per minute")
        delay_between_questions = min_delay_for_rate_limit
    
    logger.info(f"Running questions for user ID: {user_id}")
    logger.info(f"API URL: {api_url}")
    logger.info(f"Chat mode: {chat_mode}")
    logger.info(f"Total questions to ask: {len(questions_to_ask)}")
    logger.info(f"Delay between questions: {delay_between_questions:.2f} seconds")
    logger.info(f"Max requests per minute: {max_per_minute}")
    
    results = []
    start_time = time.time()
    
    for i, question in enumerate(questions_to_ask, 1):
        logger.info(f"Question {i}/{len(questions_to_ask)}: {question}")
        
        # Ask the question via API
        result = await ask_question_api(user_id, question, api_url, chat_mode)
        
        # Log the answer
        if result["answer"]:
            logger.info(f"Answer: {result['answer'][:200]}...")
            
            # Log number of chunks and their page numbers if available
            num_chunks = len(result.get("chunks", []))
            logger.info(f"Retrieved {num_chunks} relevant chunks")
            
            # Sample metadata from first chunk if available
            if num_chunks > 0 and "metadata" in result["chunks"][0]:
                metadata = result["chunks"][0]["metadata"]
                if "pages" in metadata:
                    logger.info(f"Sample chunk from pages: {metadata['pages']}")
        else:
            logger.info("No answer received")
        
        results.append(result)
        logger.info("-" * 80)
        
        # Add delay between questions to avoid rate limits
        if i < len(questions_to_ask):
            logger.info(f"Waiting {delay_between_questions:.2f} seconds before next question...")
            await asyncio.sleep(delay_between_questions)
    
    # Calculate total time and requests per minute
    end_time = time.time()
    total_time = end_time - start_time
    requests_per_minute = len(questions_to_ask) / (total_time / 60.0)
    
    summary = {
        "total_questions": len(results),
        "total_time_seconds": total_time,
        "requests_per_minute": requests_per_minute,
        "results": results
    }
    
    # Print summary
    logger.info("=" * 80)
    logger.info(f"SUMMARY: Processed {len(results)} questions in {total_time:.2f} seconds")
    logger.info(f"Average rate: {requests_per_minute:.2f} requests per minute")
    
    # Save results if output file specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Generate text report if specified
    if report_path:
        logger.info(f"Generating text report at {report_path}...")
        generate_text_report(results, report_path)
        logger.info(f"Text report saved to {report_path}")

def generate_text_report(results, report_path):
    """
    Generate a well-formatted text report of all questions and answers
    
    Args:
        results: List of result objects with questions and answers
        report_path: Path to save the report to
    """
    with open(report_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("DOCUMENT QUESTION & ANSWER REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            # Write question with section number
            f.write(f"QUESTION {i}:\n")
            f.write(f"{result['question']}\n\n")
            
            # Write answer
            f.write("ANSWER:\n")
            if result.get("answer") and not result["answer"].startswith("Error:"):
                f.write(f"{result['answer']}\n")
            else:
                f.write("No valid answer was received.\n")
            
            # Write source information
            chunks = result.get("chunks", [])
            if chunks:
                f.write("\nSOURCES:\n")
                for j, chunk in enumerate(chunks[:3], 1):  # Show up to 3 sources
                    metadata = chunk.get("metadata", {})
                    pages = metadata.get("pages", [])
                    filename = metadata.get("filename", "Unknown")
                    page_info = f"Pages: {pages}" if pages else ""
                    f.write(f"  {j}. {filename} {page_info}\n")
            
            # Add separator between questions
            f.write("\n" + "-" * 80 + "\n\n")

if __name__ == "__main__":
    asyncio.run(main())



