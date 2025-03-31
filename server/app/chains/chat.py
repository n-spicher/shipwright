from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from ..llm.config import get_gemini_client, get_chat_template

def create_chat_chain(api_key: str = None):
    """
    Creates a basic chat chain that can be used for simple conversations using Google's Gemini model.
    
    Args:
        api_key (str, optional): Google API key. If not provided, will look for GOOGLE_API_KEY env var.
    
    Returns:
        A chain that can be used for chat interactions
    """
    llm = get_gemini_client(api_key)
    prompt = get_chat_template()
    
    chain = (
        {"input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain 