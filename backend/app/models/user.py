from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    firebase_uid = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    
    keywords = relationship("Keyword", back_populates="user") 