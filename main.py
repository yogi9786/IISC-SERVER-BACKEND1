from datetime import timedelta
from email import errors
import os
from typing import List, Optional
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, Depends, UploadFile
from huggingface_hub import paper_info
import openai
from pydantic import BaseModel, Field
from schema.schemas import ChatRequest
from config.database import MongoClient
import redis
import uvicorn
from routes.route import create_access_token, get_current_user, router  
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from conf.configg import CLIENT_ID, CLIENT_SECRET
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import bcrypt
import logging
from passlib.context import CryptContext  # Add this import
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from starlette.background import BackgroundTasks
from fastapi import Query
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from twilio.rest import Client

# Set up passlib for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Mount static files to serve CSS, JS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session Middleware (Required for OAuth login)
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")  # Change this to a secure key

app.include_router(router, prefix="/api", tags=["API"])  # ✅ Correct way

# CORS Middleware Setup (Fix)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Include Router
app.include_router(router)

# Product Model
class Product(BaseModel):
    name: str
    description: str
    price: float
    category: str
    stock: int
    image_url: Optional[str] = None
    
    
# Pydantic Models
class ReviewCreate(BaseModel):
    product_id: str
    user_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    product_id: str
    user_id: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    approved: bool

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["merch_store"]
products_collection = db["products"]
reviews_collection = db["reviews"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    client = MongoClient(MONGO_URI)
    db = client["your_database"]
    tokens_collection = db["tokens"]
    print(" MongoDB Connected Successfully!")
except Exception as e:
    print(" MongoDB Connection Error:", e)
    
    
conf = ConnectionConfig(
    MAIL_USERNAME="yogesh.v@xtransmatrix.com",
    MAIL_PASSWORD="Yogeshv@123",
    MAIL_FROM="yogesh.v@xtransmatrix.com",
    MAIL_PORT=587,  # Use 465 for SSL
    MAIL_SERVER="smtp.gmail.com",  # Change if using another provider
    MAIL_FROM_NAME="IISc Training",
    MAIL_STARTTLS=True,  # Required for TLS
    MAIL_SSL_TLS=False   # Use True if using SSL (PORT 465)
)

async def send_welcome_email(email: str, name: str):
    """Send a welcome email with a subscribe option."""
    
    # Email content with a Subscribe button
    html = f"""
    <html>
        <body>
            <h2>Welcome to IISc Training, {name}!</h2>
            <p>We are excited to have you on board.</p>
            <p>At IISc, we specialize in design training.</p>
            <p>Want to stay updated? Subscribe to our latest updates and offers!</p>
            
            <a href="http://localhost:8000/subscribe?email={email}" 
               style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
               Subscribe Now
            </a>
            
            <p>Best Regards,<br>IISc Team</p>
        </body>
    </html>
    """

    # Email message
    message = MessageSchema(
        subject="Welcome to IISc Training!",
        recipients=[email],  
        body=html,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)



oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id="474230928320-d76ijvbhg1pqulgi8gngo9278rrct960.apps.googleusercontent.com",
    client_secret="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",
    client_kwargs={
        'scope': 'email openid profile',
        'redirect_uri': 'http://localhost:8000/auth'
    }
)

# Cloudinary Config
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)




templates = Jinja2Templates(directory="templates")


# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Register routes
app.include_router(router, prefix="/api", tags=["API"])

# Helper function to hash a password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


# Helper Function
def product_helper(product) -> dict:
    return {
        "id": str(product["_id"]),
        "name": product["name"],
        "description": product["description"],
        "price": product["price"],
        "category": product["category"],
        "stock": product["stock"],
        "image_url": product.get("image_url", ""),
    }
    
# Function to Convert MongoDB Document to Pydantic Model
def review_serializer(review):
    return {
        "id": str(review["_id"]),
        "product_id": review["product_id"],
        "user_id": review["user_id"],
        "rating": review["rating"],
        "comment": review.get("comment"),
        "created_at": review["created_at"],
        "approved": review["approved"]
    }


@app.get("/")
def index(request: Request):
    user = request.session.get("user")
    if user:
        return RedirectResponse("/welcome")

    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/welcome")
async def welcome(request: Request):
    # Retrieve user info from session
    user_info = request.session.get("user")
    
    if user_info:
        # Render the welcome page with user information
        return templates.TemplateResponse("welcome.html", {"request": request, "user": user_info})
    else:
        # If no session user info is found, redirect to login
        return RedirectResponse("/auth")


@app.get("/login")
async def login(request: Request):
    url = request.url_for("auth")
    return await oauth.google.authorize_redirect(request, url)


@app.get("/auth")
async def auth(request: Request):
    # Try to retrieve the access token from Google OAuth
    token = await oauth.google.authorize_access_token(request)

    if token:
        user = token.get("userinfo")
        
        if user:
            # Store user info in session
            request.session["user"] = dict(user)
            
            # Hash a password using the google ID (as an example) - this is for simulation
            hashed_password = pwd_context.hash(user["sub"])

            try:
                # Prepare data to insert into the MongoDB tokens_collection
                token_data = {
                    "google_id": user["sub"],  # Google User ID
                    "email": user["email"],    # User's email
                    "name": user["name"],      # User's name
                    "picture": user.get("picture"),  # Profile picture URL
                    "access_token": token.get("access_token"),  # OAuth access token
                    "refresh_token": token.get("refresh_token"),  # OAuth refresh token
                    "expires_in": token.get("expires_in"),  # Token expiration time
                    "token_type": token.get("token_type"),  # Token type (usually "bearer")
                    "issued_at": datetime.utcnow(),  # Store the timestamp when the token was issued
                    "expires_at": datetime.utcnow().timestamp() + token.get("expires_in"),  # Calculate expiration time
                    "hashed_password": hashed_password  # Add the hashed password here
                }

                # Insert the token data into the tokens collection
                await tokens_collection.insert_one(token_data)

                # Redirect to welcome page after successful storage
                return RedirectResponse("/welcome")

            except Exception:
                # If something goes wrong while inserting into MongoDB, just redirect to welcome
                return RedirectResponse("/welcome")
    
    # If token or user info are not available, just redirect to welcome page
    return RedirectResponse("/welcome")


@app.get("/logout")
def logout(request: Request):
    request.session.pop("user", None)
    request.session.clear()
    return RedirectResponse("/")


@app.get("/subscribe")
async def subscribe(email: str = Query(...)):
    """Subscribe the user to IISc updates."""
    
    user = db["users"].find_one({"email": email})
    
    if not user:
        return {"message": "User not found!"}

    # Update subscription status
    db["users"].update_one({"email": email}, {"$set": {"subscribed": True}})

    return {"message": "Subscription successful!"}


# Add Product
@app.post("/products/", response_model=dict)
async def add_product(product: Product):
    product_dict = product.dict()
    result = products_collection.insert_one(product_dict)
    created_product = products_collection.find_one({"_id": result.inserted_id})
    return product_helper(created_product)

# Upload Product Image
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    result = cloudinary.uploader.upload(file.file)
    return {"image_url": result["secure_url"]}

# Get All Products (with Search & Filters)
@app.get("/products/", response_model=List[dict])
async def get_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, pattern="^(price|name|stock)$"),
    order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
):
    query = {}
    if category:
        query["category"] = category
    if min_price:
        query["price"] = {"$gte": min_price}
    if max_price:
        query["price"]["$lte"] = max_price if "price" in query else {"$lte": max_price}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    sort_order = 1 if order == "asc" else -1
    products = list(products_collection.find(query).sort(sort_by, sort_order))
    return [product_helper(p) for p in products]

# Get Single Product
@app.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: str):
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_helper(product)

# Update Product
@app.put("/products/{product_id}", response_model=dict)
async def update_product(product_id: str, updated_product: Product):
    result = products_collection.update_one(
        {"_id": ObjectId(product_id)}, {"$set": updated_product.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product not found or no changes made")
    updated = products_collection.find_one({"_id": ObjectId(product_id)})
    return product_helper(updated)

# Delete Product
@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    result = products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


# 📝 1️⃣ Post a Review (User)
@app.post("/mainproducts", response_model=ReviewResponse)
async def post_review(review: ReviewCreate):
    review_data = {
        "product_id": review.product_id,
        "user_id": review.user_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": datetime.utcnow(),
        "approved": False  # Reviews need admin approval
    }
    result = reviews_collection.insert_one(review_data)
    return review_serializer(reviews_collection.find_one({"_id": result.inserted_id}))

# 🔍 2️⃣ Get Reviews for a Product (Approved Only)
@app.get("/{product_id}", response_model=List[ReviewResponse])
async def get_reviews(product_id: str):
    reviews = reviews_collection.find({"product_id": product_id, "approved": True})
    return [review_serializer(review) for review in reviews]

# 📊 3️⃣ Get Average Rating for a Product
@app.get("/{product_id}/average-rating")
async def get_average_rating(product_id: str):
    reviews = reviews_collection.find({"product_id": product_id, "approved": True})
    ratings = [review["rating"] for review in reviews]
    if not ratings:
        return {"product_id": product_id, "average_rating": None, "total_reviews": 0}
    return {"product_id": product_id, "average_rating": sum(ratings) / len(ratings), "total_reviews": len(ratings)}

# ✅ 4️⃣ Approve a Review (Admin)
@app.put("/{review_id}/approve")
async def approve_review(review_id: str):
    result = reviews_collection.update_one({"_id": ObjectId(review_id)}, {"$set": {"approved": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review approved"}

@router.delete("/{review_id}")
async def delete_review(review_id: str):
    try:
        # Validate if the review_id is a valid ObjectId
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=400, detail="Invalid Review ID format")

        result = reviews_collection.delete_one({"_id": ObjectId(review_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Review not found")

        return {"message": "Review deleted successfully"}

    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid Review ID format")
    
@app.post("/chat/")
async def chat(request: ChatRequest):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": request.message}]
        )
        return {"response": response["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



