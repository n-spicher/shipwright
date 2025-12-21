# Shipwright

Shipwright is a FastAPI-based application designed for construction document analysis and management. It helps users extract, process, and query information from construction documents using AI-powered features.

## Features

- **Document Processing**: Upload and process PDF construction documents
- **Keyword Extraction**: Automatically extract important keywords and their associated instructions from documents
- **AI-Powered Document Chat**: Ask questions about your documents and get relevant answers
- **Specialized Chat Modes**: Different chat modes for General Contractors, Mechanical Contractors, and Electrical Contractors
- **Persistent Storage**: Document storage with vector embeddings for semantic search
- **User Management**: Multi-user support with authentication
- **RESTful API**: Comprehensive API for frontend integration

## Technology Stack

- **Backend Framework**: FastAPI
- **Database**: SQLAlchemy with SQLite
- **Vector Database**: ChromaDB for semantic search
- **AI/ML**: Google Gemini (1.5-flash) for LLM capabilities
- **PDF Processing**: PyPDF2 for PDF text extraction
- **Authentication**: Passlib and Python Jose for secure authentication

## API Endpoints

### User Management
- `POST /users/`: Create a new user
- `GET /users/{user_id}`: Get user details

### Document Management
- `POST /upload-pdf`: Upload and process a PDF document
- `GET /documents/{user_id}`: List all documents for a user
- `DELETE /documents/{user_id}/{document_id}`: Delete a specific document
- `DELETE /all-documents/{user_id}`: Delete all documents for a user

### Keyword Management
- `POST /keywords/`: Create a new keyword
- `GET /keywords/{user_id}`: List all keywords for a user
- `GET /keywords/{user_id}/{keyword_id}`: Get a specific keyword
- `PUT /keywords/{user_id}/{keyword_id}`: Update a keyword
- `DELETE /keywords/{user_id}/{keyword_id}`: Delete a keyword
- `POST /keyword-upload`: Extract and save keywords from a PDF

### Document Chat
- `POST /ask`: Ask a question about a document
- `GET /chat_modes`: List available chat modes

### System
- `GET /ping`: Simple ping endpoint
- `GET /health`: Health check endpoint

## Getting Started

### Prerequisites
- Python 3.8+
- Google API key for Gemini LLM

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/shipwright.git
   cd shipwright
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   GOOGLE_API_KEY=your_google_api_key
   ```

5. Start the server:
   ```
   uvicorn main:app --reload
   ```

The API will be available at http://localhost:8000. API documentation is available at http://localhost:8000/docs.

## Database Schema

### Users
- `id`: Primary key
- `email`: Unique email address
- `username`: Unique username
- `hashed_password`: Securely hashed password
- `is_active`: Boolean indicating active status

### Documents
- `id`: UUID primary key
- `user_id`: Foreign key to users
- `filename`: Document filename
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Keywords
- `id`: Primary key
- `user_id`: Foreign key to users
- `term`: The keyword term
- `example_text`: Instructions or context for the keyword

## How It Works

1. **Document Upload**: Users upload construction documents in PDF format
2. **Document Processing**: The system extracts text and creates vector embeddings
3. **Keyword Extraction**: Important terms and instructions are extracted using Gemini LLM
4. **Document Query**: Users can ask questions about documents
5. **AI-Powered Responses**: The system uses semantic search to find relevant document sections and generates answers using the Gemini LLM

## Ask Questions Script

The `ask_questions.py` script provides a command-line interface for batch-processing multiple questions against your documents. This is useful for testing, benchmarking, or generating comprehensive reports about document content.

### Features
- Batch processing of predefined questions
- Rate limiting to avoid API overload
- Automatic retry with exponential backoff for failed requests
- Detailed logging and progress tracking
- Output formatting as both JSON and human-readable text reports
- Support for different chat modes (GC, MC, EC)

### Usage

```
python scripts/ask_questions.py [user_id] [options]
```

#### Required Arguments
- `user_id`: The ID of the user whose documents should be queried

#### Optional Arguments
- `--api-url`: API URL (default: http://localhost:8000)
- `--output`, `-o`: Output file for JSON results
- `--limit`, `-l`: Limit number of questions to process
- `--mode`, `-m`: Chat mode to use [NONE, GC, MC, EC] (default: NONE)
- `--delay`, `-d`: Delay between questions in seconds (default: 10.0)
- `--max-per-minute`: Maximum requests per minute (default: 5)
- `--report`, `-r`: Text report file path (default: report.txt)

### Example Commands

Basic usage:
```
python scripts/ask_questions.py 1
```

Specifying options:
```
python scripts/ask_questions.py 1 --mode GC --limit 5 --output results.json --report report.txt
```

Using with remote API:
```
python scripts/ask_questions.py 1 --api-url https://api.example.com --mode EC
```

### Output

The script generates two types of output:
1. **JSON output** (optional): Contains detailed information about each question, answer, and the context chunks used
2. **Text report**: A human-readable format with questions, answers, and source information

## License

[Specify your license here] 