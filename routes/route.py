from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from passlib.context import CryptContext
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
from config.database import db  # connected "database.py" for MongoDB connection
from typing import List, Optional
from schema.schemas import UserCreateSchema
from schema.schemas import UserLoginSchema
from schema.schemas import TodoSchema
from schema.schemas import UpdateTodoSchema
from schema.schemas import ContactFormSchema
from fastapi import FastAPI, UploadFile, File
import re

app = FastAPI()


# App Setup
router = APIRouter()

# MongoDB collections
todos_collection = db["todos"]
users_collection = db["users"]
contacts_collection = db["contacts"]

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Helper functions for password hashing and JWT creation/validation
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Helper function to return a validated dictionary for Todo
def todo_helper(todo) -> dict:
    return {
        "id": str(todo.get("_id", "")),  # Default to an empty string if "_id" is missing
        "name": todo.get("name", ""),   # Default to an empty string if "name" is missing
        "email": todo.get("email", ""), # Default to an empty string if "email" is missing
        "message": todo.get("message", "") # Default to an empty string if "message" is missing
    }
    
@validator("name")
def validate_name(cls, value):
    # Check if name contains any digits
    if any(char.isdigit() for char in value):
        raise ValueError("Name cannot contain numbers.")
    return value

@validator("email")
def validate_email(cls, value):
    # Validate email format using regex
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, value):
            raise ValueError("Invalid email format.")
        return value

# Register User Endpoint
@router.post("/register", response_description="Register a new user")
async def register_user(user: UserCreateSchema):
    # Check if email already exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and store the user in the database
    hashed_password = hash_password(user.password)
    user_data = user.dict()
    user_data["password"] = hashed_password
    result = users_collection.insert_one(user_data)

    return {"message": "User registered successfully", "id": str(result.inserted_id)}

# Login User Endpoint
@router.post("/login", response_description="Login and get token")
async def login_user(user: UserLoginSchema):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Protect routes with JWT token (example)
def get_current_user(token: str = Depends(verify_token)):
    payload = token
    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return email

# Todo Routes
@router.post("/todos/", response_description="Add new todo")
async def create_todo(todo: TodoSchema):
    new_todo = todo.dict()
    result = todos_collection.insert_one(new_todo)
    created_todo = todos_collection.find_one({"_id": result.inserted_id})
    return todo_helper(created_todo)

@router.get("/todos/", response_description="List all todos")
async def get_todos():
    todos = []
    for todo in todos_collection.find():
        todos.append(todo_helper(todo))
    return todos

@router.get("/todos/{id}", response_description="Get a single todo by ID")
async def get_todo_by_id(id: str):
    todo = todos_collection.find_one({"_id": ObjectId(id)})
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo_helper(todo)

@router.put("/todos/{id}", response_description="Update a todo by ID")
async def update_todo(id: str, todo: UpdateTodoSchema):
    update_data = {k: v for k, v in todo.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    result = todos_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.modified_count > 0:
        updated_todo = todos_collection.find_one({"_id": ObjectId(id)})
        return todo_helper(updated_todo)
    raise HTTPException(status_code=404, detail="Todo not found")

@router.delete("/todos/{id}", response_description="Delete a todo by ID")
async def delete_todo(id: str):
    result = todos_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count > 0:
        return {"message": "Todo deleted successfully"}
    raise HTTPException(status_code=404, detail="Todo not found")

# POST endpoint
@router.post("/contacts/", response_description="Submit a contact form")
async def submit_contact_form(contact_form: ContactFormSchema):
    contact_data = contact_form.dict()

    # Simulating database insertion (replace with actual DB logic)
    result = {"_id": "12345", **contact_data}

    return {
        "id": result["_id"],
        "name": result["name"],
        "email": result["email"],
        "message": result["message"],
    }
    
# submissions data
@router.get("/contacts/data", response_description="List all contact form submissions")
async def get_contact_forms():
    contacts = []
    for contact in contacts_collection.find():
        contacts.append({
            "id": str(contact["_id"]),
            "name": contact["name"],
            "email": contact["email"],
            "message": contact["message"]
        })
    return contacts



