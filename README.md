# Shipwright - Construction Estimator Chatbot

A full-stack application that combines a FastAPI backend service with a React frontend to create a commercial construction estimator chatbot. Users can upload PDFs, view them in the browser, and chat with an AI assistant about the document contents.

## Project Structure

```
├── server/                 # Backend service
│   ├── app/
│   │   ├── database/      # Database configuration
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic models
│   │   ├── utils/         # Utility functions
│   │   ├── llm/           # LangChain configuration
│   │   └── chains/        # LangChain chain implementations
│   ├── main.py            # Main application file
│   └── requirements.txt   # Backend dependencies
│
└── client/                # Frontend application
    ├── src/
    │   ├── components/   # Reusable UI components
    │   ├── pages/        # Page-level components
    │   ├── contexts/     # React context providers
    │   ├── utils/        # Utility functions
    │   ├── hooks/        # Custom React hooks
    │   └── assets/       # Static assets
    └── package.json      # Frontend dependencies
```

## Backend Setup

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

## Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory with your Firebase configuration:
```
REACT_APP_FIREBASE_API_KEY=your_api_key
REACT_APP_FIREBASE_AUTH_DOMAIN=your_auth_domain
REACT_APP_FIREBASE_PROJECT_ID=your_project_id
REACT_APP_FIREBASE_STORAGE_BUCKET=your_storage_bucket
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
REACT_APP_FIREBASE_APP_ID=your_app_id
```

3. Start the development server:
```bash
npm start
```

The frontend will start at `http://localhost:3000`

## Features

### Backend
- FastAPI-based REST API
- SQLite database with SQLAlchemy ORM
- ChromaDB integration for vector storage
- LangChain with Google's Gemini model for AI capabilities
- JWT-based authentication
- CORS middleware configured

### Frontend
- User Authentication with Firebase
- PDF Management (upload, view, delete)
- Interactive Chat Interface
- Document References in Chatbot Responses
- Modern UI with Chakra UI

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

## Dependencies

### Backend
- FastAPI: Web framework
- SQLAlchemy: Database ORM
- ChromaDB: Vector database
- LangChain: AI/LLM framework
- LangChain-Google-GenAI: Google Gemini integration
- LangChain-Community: Community components
- Python-Jose: JWT token handling
- Passlib: Password hashing
- Email-Validator: Email validation
- Python-Multipart: Form data handling

### Frontend
- React: UI framework
- Firebase: Authentication and Storage
- Chakra UI: Component library
- react-pdf: PDF viewer
- React Router: Navigation

## Security Features

- Password hashing using bcrypt
- Email validation
- Unique email and username constraints
- CORS middleware configured
- API key handling for Google Gemini integration
- Firebase Authentication for frontend

## Deployment

### Frontend (Vercel)
1. Create a Vercel account if you don't have one
2. Install the Vercel CLI: `npm i -g vercel`
3. Deploy: `vercel`

### Backend (Render)
1. Create a Render account
2. Connect your GitHub repository
3. Configure environment variables
4. Deploy the FastAPI application
