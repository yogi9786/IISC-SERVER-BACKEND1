from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

# User Schema
class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

# Define Pydantic models for other operations (Todo and Contact Form)
class TodoSchema(BaseModel):
    name: str
    email: EmailStr
    message: str

class UpdateTodoSchema(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]
    message: Optional[str]

class TodoResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    message: str

class Config:
        form_mode = True

class ContactFormSchema(BaseModel):
    name: str = Field(..., example="John Doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    message: str = Field(..., example="Hello! This is a test message.")

class Data(BaseModel):
    # id: str
    project: str
    messages: str

class TodoSchema(BaseModel):
    name: str
    description: str
    message: str
    
# Request model
class ChatRequest(BaseModel):
    message: str


# Product Model
class Product(BaseModel):
    name: str
    description: str
    price: float
    category: str
    stock: int
    image_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "description": "A sample description",
                "message": "Hello, this is a sample message."
            }
        }

class UpdateTodoSchema(BaseModel):
    name: Optional[str]
    description: Optional[str]
    message: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jane Doe",
                "description": "Updated description",
                "message": "This is an updated message."
            }
        }
