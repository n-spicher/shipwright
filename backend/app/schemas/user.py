from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserProfile(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    is_active: bool
    subscription_tier: str = "free"
    subscription_status: str = "active"
    subscription_current_period_end: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SubscriptionTier(BaseModel):
    tier: str
    name: str
    price: float
    price_id: Optional[str] = None
    features: List[str]

class SubscriptionStatus(BaseModel):
    tier: str
    status: str
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False 
