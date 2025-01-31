import os
from fastapi import FastAPI, Request
import redis
import uvicorn
from routes.route import router  # ✅ Importing router correctly
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Register routes
app.include_router(router, prefix="/api", tags=["API"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

# Root endpoint
@app.get("/", response_class=HTMLResponse, tags=["Root"])
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})