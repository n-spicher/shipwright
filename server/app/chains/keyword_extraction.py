from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

def create_keyword_extraction_chain():
    prompt = PromptTemplate(
        input_variables=["document_content"],
        template="""You are an expert at analyzing construction documents and extracting important keywords and their associated instructions.

The following is a set of instructions for keywords and what to do with them. Parse the document into a structured output with term (the keyword) and example_text (the instructions on what to do with that keyword).

Document Content:
{document_content}

Please analyze the document and extract keywords along with their associated instructions. For each keyword:
1. Identify important terms, specifications, or requirements
2. Extract the relevant context or instructions that explain how to handle or implement that keyword
3. Format the output as a JSON array of objects with 'term' and 'example_text' string fields
   3a. The 'term' should be a single word or phrase that is the keyword
   3b. The 'example_text' should be a string that is the exact text of the targets from the document comma separated for different values

Example output format:
[
    {{"term": "BOD", "example_text": "ACCEPTABLE MANUFACTURERS:,MANUFACTURERS:,Base of design:,Base:,Optional:"}}
    {{"term": "base of design", "example_text": "ACCEPTABLE MANUFACTURERS:,MANUFACTURERS:,Base of design:,Base:,Optional:"}}
]

"""
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.1
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain