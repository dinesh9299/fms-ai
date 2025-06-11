from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    role: str = Field(default="user")
    department: str


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
