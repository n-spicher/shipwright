from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
from app.schemas.keyword_extraction import KeywordExtraction, KeywordExtractionOutput
from dotenv import load_dotenv

load_dotenv()

def create_keyword_extraction_chain():
    """
    Creates a function that extracts keywords from document content.
    Completely avoids templates and directly builds prompts.
    """
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.1
    )
    
    def build_prompt(document_content):
        """Build the prompt without using a template string."""
        return (
            "You are an expert at analyzing construction documents and extracting important keywords and their associated instructions.\n"
            "Parse the following document into a structured output with term (the keyword) and example_text (the instructions on what to do with that keyword).\n"
            "These instructions will be used to create a prompt for a chatbot to answer questions about the document so structure them in a way that is helpful for that.\n\n"
            f"Document Content:\n{document_content}\n\n"
            "1. Identify important terms, specifications, or requirements\n"
            "2. Extract the relevant context or instructions that explain how to handle or implement that keyword\n"
            "3. Format the output as a JSON array of objects with 'term' and 'example_text' string fields\n"
            "   3a. The 'term' should be a single word or phrase that is the keyword\n"
            "   3b. The 'example_text' should be a string that is the exact text of the targets from the document comma separated for different values\n\n"
            "You MUST follow this output format exactly - output ONLY a valid JSON array of objects like this:\n"
            "[\n"
            "    {\"term\": \"BOD\", \"example_text\": \"ACCEPTABLE MANUFACTURERS:,MANUFACTURERS:,Base of design:,Base:,Optional:\"},\n"
            "    {\"term\": \"base of design\", \"example_text\": \"ACCEPTABLE MANUFACTURERS:,MANUFACTURERS:,Base of design:,Base:,Optional:\"}\n"
            "]\n\n"
            "Do not include any explanations, headers, or additional text outside the JSON array. Return ONLY the JSON array."
        )
    
    # Define the extraction function
    def extract_keywords(inputs):
        # Ensure the inputs are in correct format
        if not isinstance(inputs, dict):
            raise ValueError(f"Expected inputs to be a dictionary, got {type(inputs)}")
        
        # Make sure document_content is in the inputs
        if "document_content" not in inputs:
            raise ValueError("Input must contain 'document_content' key")
        
        # Build the prompt directly
        document_content = inputs["document_content"]
        prompt = build_prompt(document_content)
        
        try:
            # Directly invoke the LLM
            response = llm.invoke(prompt)
            
            # Extract the text from the response
            raw_output = response.content
            
            try:
                # Clean the raw output by removing markdown code blocks if present
                cleaned_output = raw_output
                
                # Handle markdown code blocks (```json ... ```)
                if raw_output.startswith('```'):
                    # Find where the content starts after the first newline
                    content_start = raw_output.find('\n')
                    if content_start != -1:
                        # Find where the closing ``` is
                        content_end = raw_output.rfind('```')
                        if content_end != -1:
                            # Extract just the content between the markdown tags
                            cleaned_output = raw_output[content_start + 1:content_end].strip()
                
                # Parse the JSON array
                keywords_data = json.loads(cleaned_output)
                
                # Create KeywordExtraction objects using the proper schema
                keyword_items = [
                    KeywordExtraction(term=item['term'], example_text=item['example_text']) 
                    for item in keywords_data
                ]
                
                # Return structured results using the proper schema
                return KeywordExtractionOutput(keywords=keyword_items)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Raw output: {raw_output}")
                # Try a more aggressive cleanup approach
                try:
                    # Strip all non-JSON content
                    start_idx = raw_output.find('[')
                    end_idx = raw_output.rfind(']') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_only = raw_output[start_idx:end_idx]
                        keywords_data = json.loads(json_only)
                        keyword_items = [
                            KeywordExtraction(term=item['term'], example_text=item['example_text']) 
                            for item in keywords_data
                        ]
                        return KeywordExtractionOutput(keywords=keyword_items)
                except Exception as inner_e:
                    print(f"Secondary parsing attempt failed: {str(inner_e)}")
                return KeywordExtractionOutput(keywords=[])
        except Exception as e:
            print(f"Error invoking LLM: {str(e)}")
            raise
    
    return extract_keywords