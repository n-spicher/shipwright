# Shipwright

A FastAPI-based backend service with SQLite database, ChromaDB integration, and LangChain with Google's Gemini model for AI capabilities.

## Project Structure

```
server/
├── app/
│   ├── database/         # Database configuration
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic models for request/response
│   ├── utils/           # Utility functions
│   ├── llm/             # LangChain configuration
│   └── chains/          # LangChain chain implementations
├── main.py              # Main application file
└── requirements.txt     # Project dependencies
```

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export GOOGLE_API_KEY=your_api_key_here  # Required for Gemini functionality
```

4. Run the server:
```bash
python main.py
```

The server will start at `http://localhost:8010`

## API Endpoints

### Health Check
- **GET** `/ping`
  - Simple health check endpoint
  - Returns: `{"message": "pong"}`

### Users

#### Create User
- **POST** `/users/`
  - Creates a new user
  - Request body:
    ```json
    {
        "email": "user@example.com",
        "username": "username",
        "password": "yourpassword"
    }
    ```
  - Returns: Created user object (excluding password)

#### Get User
- **GET** `/users/{user_id}`
  - Retrieves a user by ID
  - Returns: User object (excluding password)

### AI Chat

#### Chat with AI
- **POST** `/chat`
  - Sends a message to the AI and gets a response using Google's Gemini model
  - Request body:
    ```json
    {
        "message": "Your message here",
        "api_key": "your_GOOGLE_API_KEY"  // Optional if GOOGLE_API_KEY env var is set
    }
    ```
  - Returns: `{"response": "AI's response"}`

## Example Usage

Create a new user:
```bash
curl -X POST http://localhost:8010/users/ \
-H "Content-Type: application/json" \
-d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "mypassword123"
}'
```

Get user information:
```bash
curl http://localhost:8010/users/1
```

Chat with AI:
```bash
curl -X POST http://localhost:8010/chat \
-H "Content-Type: application/json" \
-d '{
    "message": "What is the capital of France?",
    "api_key": "your_GOOGLE_API_KEY"
}'
```

## Dependencies

- FastAPI: Web framework
- SQLAlchemy: Database ORM
- ChromaDB: Vector database
- LangChain: AI/LLM framework
- LangChain-Google-GenAI: Google Gemini integration for LangChain
- LangChain-Community: Community components for LangChain
- Python-Jose: JWT token handling
- Passlib: Password hashing
- Email-Validator: Email validation
- Python-Multipart: Form data handling

## Security Features

- Password hashing using bcrypt
- Email validation
- Unique email and username constraints
- CORS middleware configured (currently allowing all origins - should be restricted in production)
- API key handling for Google Gemini integration 