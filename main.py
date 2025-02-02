import os
from fastapi import FastAPI, Request
import redis
import uvicorn
from routes.route import router  
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from conf.configg import CLIENT_ID, CLIENT_SECRET
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="add any string...")
app.mount("/static", StaticFiles(directory="static"), name="static")

# OAuth
oauth = OAuth()
oauth.register(
    name="google",
    client_id="client_id",
    client_secret="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",
    authorize_url="client_secret",
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
    redirect_uri="http://localhost:8000/auth",  # Check this line
)



templates = Jinja2Templates(directory="templates")


app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Session Middleware (Required for OAuth login)
app.add_middleware(SessionMiddleware, secret_key="your_very_secure_secret_key")


# Middleware for CORS & Sessions
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")  # Change to a secure key
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Register routes
app.include_router(router, prefix="/api", tags=["API"])

if __name__ == "__main__":
    uvicorn.run(
        app = "main:app", 
        host="localhost",
        port=8000,
        reload=True,
    )
        

# Root endpoint
@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/set-session")
async def set_session(request: Request):
    request.session["user"] = "John Doe"
    return {"message": "Session set!"}

@app.get("/get-session")
async def get_session(request: Request):
    user = request.session.get("user", "No session found")
    return {"user": user}

@app.get('/welcome')
def welcome(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse('/')
    return templates.TemplateResponse(
        name='welcome.html',
        context={'request': request, 'user': user}
    )


@app.get("/login")
async def login(request: Request):
    url = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, url)


@app.get('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        return templates.TemplateResponse(
            name='error.html',
            context={'request': request, 'error': e.error}
        )
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse('welcome')


@app.get('/logout')
def logout(request: Request):
    request.session.pop('user')
    request.session.clear()
    return RedirectResponse('/')