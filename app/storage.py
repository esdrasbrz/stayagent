from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import asyncio

from app.models import JobStatus, JobStateEnum, StayResult

class JobStore(ABC):
    @abstractmethod
    async def create_job(self, operation_id: str) -> None:
        pass

    @abstractmethod
    async def update_job_status(self, operation_id: str, status: JobStateEnum, error: Optional[str] = None) -> None:
        pass

    @abstractmethod
    async def save_results(self, operation_id: str, results: List[StayResult]) -> None:
        pass

    @abstractmethod
    async def get_job_status(self, operation_id: str) -> Optional[JobStatus]:
        pass

    @abstractmethod
    async def get_job_results(self, operation_id: str) -> Optional[List[StayResult]]:
        pass

    @abstractmethod
    async def attach_task(self, operation_id: str, task: asyncio.Task) -> None:
        """Stores the asyncio Task so it can be cancelled later (in-memory only feature)."""
        pass

    @abstractmethod
    async def cancel_job(self, operation_id: str) -> bool:
        """Attempts to cancel an active job. Returns True if cancelled."""
        pass


class InMemoryJobStore(JobStore):
    def __init__(self):
        self._statuses: Dict[str, JobStatus] = {}
        self._results: Dict[str, List[StayResult]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    async def create_job(self, operation_id: str) -> None:
        self._statuses[operation_id] = JobStatus(
            operation_id=operation_id,
            status=JobStateEnum.PENDING
        )

    async def update_job_status(self, operation_id: str, status: JobStateEnum, error: Optional[str] = None) -> None:
        if operation_id in self._statuses:
            self._statuses[operation_id].status = status
            if error:
                self._statuses[operation_id].error = error

    async def save_results(self, operation_id: str, results: List[StayResult]) -> None:
        self._results[operation_id] = results
        await self.update_job_status(operation_id, JobStateEnum.COMPLETED)

    async def get_job_status(self, operation_id: str) -> Optional[JobStatus]:
        return self._statuses.get(operation_id)

    async def get_job_results(self, operation_id: str) -> Optional[List[StayResult]]:
        return self._results.get(operation_id)

    async def attach_task(self, operation_id: str, task: asyncio.Task) -> None:
        self._tasks[operation_id] = task

    async def cancel_job(self, operation_id: str) -> bool:
        task = self._tasks.get(operation_id)
        if task and not task.done():
            task.cancel()
            await self.update_job_status(operation_id, JobStateEnum.CANCELLED)
            return True
        elif operation_id in self._statuses:
            await self.update_job_status(operation_id, JobStateEnum.CANCELLED)
            return True
        return False
