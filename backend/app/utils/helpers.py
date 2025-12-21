import re
from typing import List, Any


def get_collection_name(user_id: int):
        return f"user_pdf_documents_{user_id}"
        
def find_applicable_keywords(message: str, keywords: List[Any]) -> List[Any]:
    """
    Match keywords in a message and return applicable keywords
    
    Args:
        message (str): User message to analyze
        keywords (List[Any]): List of keyword objects with term attribute
        
    Returns:
        List[Any]: Filtered list of applicable keywords
    """
    applicable_keywords = []
    
    if not keywords or not message:
        return applicable_keywords
    
    # Convert message to lowercase for case-insensitive matching
    message_lower = message.lower()
    
    for keyword in keywords:
        # Skip invalid keywords
        if not keyword or not hasattr(keyword, 'term'):
            continue
            
        # Get the term and convert to lowercase
        term = keyword.term.lower() if isinstance(keyword.term, str) else ''
        
        # Skip empty terms
        if not term:
            continue
            
        # Check if the term appears as a whole word in the message
        # Using word boundary pattern \b to match whole words
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, message_lower):
            applicable_keywords.append(keyword)
    
    return applicable_keywords