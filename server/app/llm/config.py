from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Google Gemini client
def get_gemini_client(api_key: Optional[str] = None):
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Please set GOOGLE_API_KEY environment variable.")
    return ChatGoogleGenerativeAI(
        #model="gemini-1.5-pro",
        model="gemini-1.5-flash",
        GOOGLE_API_KEY=api_key,
        temperature=0.7,
        convert_system_message_to_human=True
    )

# Initialize embeddings
def get_embeddings(api_key: Optional[str] = None):
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Please set GOOGLE_API_KEY environment variable.")
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        GOOGLE_API_KEY=api_key
    )

# Basic chat template
def get_chat_template():
    return ChatPromptTemplate.from_messages([
        ("system", "You are Shipwright, a friendly AI assistant specialized in answering questions about documents. You should only use the provided context to answer questions and clearly indicate if the information is not available in the context."),
        ("human", "{input}")
    ])

# Basic chain
def get_basic_chain(api_key: Optional[str] = None):
    llm = get_gemini_client(api_key)
    prompt = get_chat_template()
    chain = prompt | llm | StrOutputParser()
    return chain 