from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum


class PlatformEnum(str, Enum):
    AIRBNB = "airbnb"
    BOOKING = "booking"


class JobStateEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SearchRequest(BaseModel):
    location: str = Field(
        ..., description="Free text location to search for, e.g. 'New York'"
    )
    checkin: date
    checkout: date
    guests: int = Field(1, ge=1)
    limit: int = Field(
        20, ge=1, le=100, description="Max number of results to fetch per platform"
    )


class StayResult(BaseModel):
    platform: PlatformEnum
    external_url: str
    name: str
    price_total: Optional[float] = None
    price_per_night: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    image_urls: List[str] = []
    features: List[str] = []


class JobStatus(BaseModel):
    operation_id: str
    status: JobStateEnum
    progress: int = 0
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    operation_id: str
    status: JobStateEnum
    results: List[StayResult] = []
