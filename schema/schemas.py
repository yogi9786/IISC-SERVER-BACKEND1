from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional

# Define the Pydantic model for user registration and login
class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

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
