import uuid
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request

from app.models import SearchRequest, JobStatus, JobResultResponse, JobStateEnum
from app.crawlers.manager import CrawlerManager
from app.storage import JobStore

logger = logging.getLogger(__name__)

router = APIRouter()

# This is a bit of dependency injection so the router knows about our store.
# In a real app we'd attach it to app.state or use Depends directly on a setup function.
# For simplicity here we assume the store will be passed around or global, but we use a global reference that gets initialized in main.py.
# We'll use a getter function.
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    if _job_store is None:
        raise RuntimeError("JobStore not initialized")
    return _job_store


def set_job_store(store: JobStore):
    global _job_store
    _job_store = store


async def crawl_background_task(
    operation_id: str,
    request: SearchRequest,
    store: JobStore,
    crawler_manager: CrawlerManager,
):
    try:
        await store.update_job_status(operation_id, JobStateEnum.RUNNING)
        logger.info(f"Starting crawl job {operation_id}")

        results = await crawler_manager.run_all(request)

        await store.save_results(operation_id, results)
        logger.info(f"Finished crawl job {operation_id} with {len(results)} results")
    except asyncio.CancelledError:
        logger.info(f"Crawl job {operation_id} cancelled")
        await store.update_job_status(operation_id, JobStateEnum.CANCELLED)
        raise
    except Exception as e:
        logger.error(f"Crawl job {operation_id} failed: {e}")
        await store.update_job_status(operation_id, JobStateEnum.FAILED, error=str(e))


@router.post("/", response_model=JobStatus)
async def start_search(
    http_request: Request,
    request: SearchRequest,
    store: JobStore = Depends(get_job_store),
):
    operation_id = str(uuid.uuid4())
    await store.create_job(operation_id)

    crawler_manager: CrawlerManager = http_request.app.state.crawler_manager

    # We use asyncio.create_task to get a cancellable Future instead of FastAPI's BackgroundTasks
    task = asyncio.create_task(
        crawl_background_task(operation_id, request, store, crawler_manager)
    )
    await store.attach_task(operation_id, task)

    status = await store.get_job_status(operation_id)
    return status


@router.get("/{operation_id}/status", response_model=JobStatus)
async def get_search_status(
    operation_id: str, store: JobStore = Depends(get_job_store)
):
    status = await store.get_job_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation ID not found")
    return status


@router.post("/{operation_id}/cancel")
async def cancel_search(operation_id: str, store: JobStore = Depends(get_job_store)):
    status = await store.get_job_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation ID not found")

    if status.status in [
        JobStateEnum.COMPLETED,
        JobStateEnum.FAILED,
        JobStateEnum.CANCELLED,
    ]:
        return {"message": "Job already finished or cancelled", "status": status.status}

    cancelled = await store.cancel_job(operation_id)
    if cancelled:
        return {"message": "Job cancelled successfully"}
    return {"message": "Could not cancel job"}


@router.get("/{operation_id}/results", response_model=JobResultResponse)
async def get_search_results(
    operation_id: str, store: JobStore = Depends(get_job_store)
):
    status = await store.get_job_status(operation_id)
    if not status:
        raise HTTPException(status_code=404, detail="Operation ID not found")

    if status.status != JobStateEnum.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Results not available. Current status is {status.status}",
        )

    results = await store.get_job_results(operation_id)
    return JobResultResponse(
        operation_id=operation_id, status=status.status, results=results or []
    )
