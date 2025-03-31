from pydantic import BaseModel

class KeywordBase(BaseModel):
    term: str
    example_text: str

class KeywordCreate(KeywordBase):
    pass

class Keyword(KeywordBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True 