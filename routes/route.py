from fastapi import APIRouter, FastAPI, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
from typing import List, Optional
import re

import uvicorn
from config.database import db 
from schema.schemas import UserCreateSchema, UserLoginSchema, TodoSchema, UpdateTodoSchema, ContactFormSchema
from fastapi.templating import Jinja2Templates

router = APIRouter()

# MongoDB collections
todos_collection = db["todos"]
users_collection = db["users"]
contacts_collection = db["contacts"]
tokens_collection = db["tokens"]

app = FastAPI()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def todo_helper(todo) -> dict:
    return {
        "id": str(todo["_id"]),
        "name": todo.get("name", ""),
        "email": todo.get("email", ""),
        "message": todo.get("message", "")
    }

@router.post("/register")
async def register_user(user: UserCreateSchema):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = user.model_dump()
    user_data["password"] = hash_password(user.password)
    result = users_collection.insert_one(user_data)

    return {"message": "User registered successfully", "id": str(result.inserted_id)}

@router.post("/login")
async def login_user(user: UserLoginSchema):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(verify_token)):
    email = token.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return email

@router.post("/todos/")
async def create_todo(todo: TodoSchema):
    new_todo = todo.dict()
    result = todos_collection.insert_one(new_todo)
    created_todo = todos_collection.find_one({"_id": result.inserted_id})
    return todo_helper(created_todo)

@router.get("/todos/")
async def get_todos():
    return [todo_helper(todo) for todo in todos_collection.find()]

@router.get("/todos/{id}")
async def get_todo_by_id(id: str):
    todo = todos_collection.find_one({"_id": ObjectId(id)})
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo_helper(todo)

@router.put("/todos/{id}")
async def update_todo(id: str, todo: UpdateTodoSchema):
    update_data = {k: v for k, v in todo.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = todos_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    if result.modified_count > 0:
        updated_todo = todos_collection.find_one({"_id": ObjectId(id)})
        return todo_helper(updated_todo)
    
    raise HTTPException(status_code=404, detail="Todo not found")

@router.delete("/todos/{id}")
async def delete_todo(id: str):
    result = todos_collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count > 0:
        return {"message": "Todo deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Todo not found")

@router.post("/contacts/")
async def submit_contact_form(contact_form: ContactFormSchema):
    result = contacts_collection.insert_one(contact_form.dict())
    contact = contacts_collection.find_one({"_id": result.inserted_id})
    return {
        "id": str(contact["_id"]),
        "name": contact["name"],
        "email": contact["email"],
        "message": contact["message"]
    }

@router.get("/contacts/data")
async def get_contact_forms():
    return [
        {"id": str(contact["_id"]), "name": contact["name"], "email": contact["email"], "message": contact["message"]}
        for contact in contacts_collection.find()
    ]

if __name__ == "__main__":
    uvicorn.run(router, host="0.0.0.0", port=8000)



