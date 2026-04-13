import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.search import router as search_router, set_job_store
from app.storage import InMemoryJobStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StayAgent API", description="Async Stay Crawler for multiple platforms")

# Apply basic CORS for potential frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Storage
store = InMemoryJobStore()
set_job_store(store)

app.include_router(search_router, prefix="/api/v1/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": "StayAgent API is running."}
