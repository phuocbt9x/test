import asyncio
import json
from src.core.loggings import get_logger
import importlib
from typing import Any, Dict, Optional
from datetime import datetime

from src.core.configs import redis_manager
from src.core.utils import utcnow

logger = get_logger(__name__)


class QueueManager:
    """
    Queue Manager using Redis

    Manages job queues for async event processing.
    """

    def __init__(self, connection: str = "redis"):
        self._connection = connection
        self._prefix = "queues"

    async def push(self, queue: str, job_data: Dict[str, Any], delay: int = 0) -> bool:
        job = {
            "id": f"{utcnow().timestamp()}_{queue}",
            "queue": queue,
            "data": job_data,
            "attempts": 0,
            "created_at": utcnow().isoformat(),
            "available_at": (
                (utcnow().timestamp() + delay) if delay else utcnow().timestamp()
            ),
        }

        queue_key = self._get_queue_key(queue)

        try:
            serialized = json.dumps(job, ensure_ascii=False)

            if delay > 0:
                score = job["available_at"]
                await redis_manager.client.zadd(
                    f"{queue_key}:delayed", {serialized: score}
                )
            else:
                await redis_manager.rpush(queue_key, serialized)

            logger.debug(f"Pushed job to queue '{queue}': {job['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to push job to queue '{queue}': {e}")
            return False

    async def pop(self, queue: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        queue_key = self._get_queue_key(queue)

        try:
            await self._migrate_delayed_jobs(queue)

            if timeout > 0:
                result = await redis_manager.client.blpop([queue_key], timeout=timeout)
                if result:
                    _, data = result
                    if isinstance(data, bytes):
                        data = data.decode()
                    return json.loads(data)
            else:
                data = await redis_manager.lpop(queue_key)
                if data:
                    return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Failed to pop job from queue '{queue}': {e}")
            return None

    async def _migrate_delayed_jobs(self, queue: str) -> None:
        queue_key = self._get_queue_key(queue)
        delayed_key = f"{queue_key}:delayed"

        try:
            now = utcnow().timestamp()
            jobs = await redis_manager.client.zrangebyscore(delayed_key, min=0, max=now)

            if jobs:
                for job_data in jobs:
                    if isinstance(job_data, bytes):
                        job_data = job_data.decode()

                    await redis_manager.rpush(queue_key, job_data)

                await redis_manager.client.zremrangebyscore(delayed_key, min=0, max=now)

                logger.debug(f"Migrated {len(jobs)} delayed jobs to queue '{queue}'")

        except Exception as e:
            logger.error(f"Failed to migrate delayed jobs: {e}")

    async def size(self, queue: str) -> int:
        queue_key = self._get_queue_key(queue)
        return await redis_manager.llen(queue_key)

    async def clear(self, queue: str) -> bool:
        queue_key = self._get_queue_key(queue)

        try:
            await redis_manager.delete(queue_key)
            await redis_manager.delete(f"{queue_key}:delayed")
            await redis_manager.delete(f"{queue_key}:failed")

            logger.info(f"Cleared queue '{queue}'")
            return True

        except Exception as e:
            logger.error(f"Failed to clear queue '{queue}': {e}")
            return False

    async def failed(
        self, queue: str, job: Dict[str, Any], exception: Exception
    ) -> None:
        failed_job = {
            **job,
            "failed_at": utcnow().isoformat(),
            "exception": str(exception),
        }

        failed_key = f"{self._get_queue_key(queue)}:failed"

        try:
            serialized = json.dumps(failed_job, ensure_ascii=False)
            await redis_manager.rpush(failed_key, serialized)

            logger.warning(
                f"Job {job.get('id')} failed on queue '{queue}': {exception}"
            )

        except Exception as e:
            logger.error(f"Failed to mark job as failed: {e}")

    def _get_queue_key(self, queue: str) -> str:
        return f"{self._prefix}:{queue}"


class QueueWorker:
    """
    Queue Worker

    Processes jobs from queues.
    """

    def __init__(self, queue_manager: QueueManager, queues: list[str] = None):
        self._queue_manager = queue_manager
        self._queues = queues or ["default"]
        self._should_stop = False

    async def work(self, sleep: int = 1) -> None:
        logger.info(f"Queue worker started for queues: {', '.join(self._queues)}")

        while not self._should_stop:
            try:
                for queue_name in self._queues:
                    await self._process_queue(queue_name)

                await asyncio.sleep(sleep)

            except Exception as e:
                logger.error(f"Queue worker error: {e}", exc_info=True)
                await asyncio.sleep(sleep)

    async def _process_queue(self, queue_name: str) -> None:
        job = await self._queue_manager.pop(queue_name, timeout=0)

        if job:
            await self._process_job(queue_name, job)

    async def _process_job(self, queue_name: str, job: Dict[str, Any]) -> None:
        job_data = job.get("data", {})
        attempts = job.get("attempts", 0)
        max_tries = job_data.get("tries", 3)

        logger.debug(
            f"Processing job {job.get('id')} (attempt {attempts + 1}/{max_tries})"
        )

        try:
            listener_class_path = job_data.get("listener_class")
            module_path, class_name = listener_class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            listener_class = getattr(module, class_name)

            event_data = job_data.get("event")
            event_class_path = event_data.get("event_name")
            event = self._deserialize_event(event_data)
            listener = listener_class()

            await listener.handle(event)

            logger.info(f"Job {job.get('id')} completed successfully")

        except Exception as e:
            logger.error(f"Job {job.get('id')} failed: {e}", exc_info=True)

            job["attempts"] = attempts + 1

            if job["attempts"] < max_tries:
                delay = 2 ** job["attempts"]
                await self._queue_manager.push(queue_name, job_data, delay=delay)
                logger.info(f"Job {job.get('id')} will retry in {delay}s")
            else:
                await self._queue_manager.failed(queue_name, job, e)

    def _deserialize_event(self, event_data: Dict[str, Any]) -> Any:
        return type("Event", (), event_data)()

    def stop(self) -> None:
        logger.info("Stopping queue worker...")
        self._should_stop = True
