from datetime import timedelta
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from huggingface_hub import paper_info
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

# Set up passlib for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Mount static files to serve CSS, JS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Session Middleware (Required for OAuth login)
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")  # Change this to a secure key

# Middleware for CORS
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["http://localhost:5173/ ", "http://localhost:5173/register", "http://localhost:5173/contact"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

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


templates = Jinja2Templates(directory="templates")


# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Register routes
app.include_router(router, prefix="/api", tags=["API"])

# Helper function to hash a password
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



