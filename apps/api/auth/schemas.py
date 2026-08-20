"""
Pydantic schemas for authentication.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserInDBBase(UserBase):
    id: int
    is_active: bool = True
    role: str = "user"

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserInDBBase):
    password_hash: str


class User(UserInDBBase):
    pass