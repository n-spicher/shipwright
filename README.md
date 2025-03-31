# Construction Estimator Chatbot

A commercial construction estimator chatbot that allows users to upload PDFs, view them in the browser, and chat with an AI assistant about the document contents.

## Features

- **User Authentication**: Sign up, login, and password recovery using Firebase Authentication
- **PDF Management**: Upload, view, and delete construction documents
- **Interactive Chat**: Ask questions about your documents and get relevant answers
- **Document References**: Chatbot responses include page references to source information

## Technology Stack

- **Frontend**: React
- **Authentication**: Firebase Authentication
- **Storage**: Firebase Storage
- **PDF Viewer**: react-pdf
- **UI Library**: Chakra UI

## Setup Instructions

1. Clone the repository
2. Install dependencies:
   ```
   npm install
   ```
3. Create a `.env` file in the root directory with your Firebase configuration:
   ```
   REACT_APP_FIREBASE_API_KEY=your_api_key
   REACT_APP_FIREBASE_AUTH_DOMAIN=your_auth_domain
   REACT_APP_FIREBASE_PROJECT_ID=your_project_id
   REACT_APP_FIREBASE_STORAGE_BUCKET=your_storage_bucket
   REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
   REACT_APP_FIREBASE_APP_ID=your_app_id
   ```
4. Start the development server:
   ```
   npm start
   ```

## Development Environments

- **Development**: Local development environment (localhost:3000)
- **Production**: Deployed on Vercel (frontend) and Render (backend)

## Deployment

### Frontend (Vercel)

1. Create a Vercel account if you don't have one
2. Install the Vercel CLI: `npm i -g vercel`
3. Deploy: `vercel`

## Project Structure

- `/src`
  - `/components`: Reusable UI components
  - `/pages`: Page-level components
  - `/contexts`: React context providers
  - `/utils`: Utility functions including Firebase config
  - `/hooks`: Custom React hooks
  - `/assets`: Static assets

## Note

This is the frontend portion of the project. The backend will be built with FastAPI and integrated later.
