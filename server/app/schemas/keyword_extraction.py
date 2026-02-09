from pydantic import BaseModel
from typing import List

class KeywordExtraction(BaseModel):
    term: str
    example_text: str

class KeywordExtractionOutput(BaseModel):
    keywords: List[KeywordExtraction] 