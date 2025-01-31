from fastapi import FastAPI, APIRouter
import redis
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# App Setup
router = APIRouter()

# Connect to Redis server
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Register routes
router.include_router(router, prefix="/router", tags=["Todos"])

# Root endpoint
@router.get("/", tags=["Root"])
async def read_root():
    return {"message": "IISC"}
