"""
Upload Queue Manager with Worker Pool and Retry Logic.
Handles scalable bulk uploads (10-1000+ files) with dynamic worker scaling.
"""
import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback
from ..core.logging_config import get_logger

logger = get_logger(__name__)

class UploadStatus(Enum):
    """Upload task status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DUPLICATE = "duplicate"

@dataclass
class UploadTask:
    """Represents a single file upload task."""
    task_id: str
    file: Any  # UploadFile or File-like object
    filename: str
    folder: Optional[str] = None
    checksum: Optional[str] = None
    status: UploadStatus = UploadStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    result: Optional[Dict] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries and self.status in [UploadStatus.FAILED, UploadStatus.RETRYING]
    
    def mark_processing(self):
        """Mark task as processing."""
        self.status = UploadStatus.PROCESSING
        self.started_at = datetime.now()
    
    def mark_success(self, result: Dict):
        """Mark task as successful."""
        self.status = UploadStatus.SUCCESS
        self.result = result
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = UploadStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def mark_duplicate(self, existing_doc: Dict):
        """Mark task as duplicate."""
        self.status = UploadStatus.DUPLICATE
        self.result = {"existing_document": existing_doc}
        self.completed_at = datetime.now()
    
    def mark_retrying(self):
        """Mark task for retry."""
        self.status = UploadStatus.RETRYING
        self.retry_count += 1

class UploadQueueManager:
    """
    Manages upload queue with dynamic worker pool and retry logic.
    Scales workers based on queue size and system load.
    """
    
    def __init__(
        self,
        min_workers: int = 5,
        max_workers: Optional[int] = None,  # None = unlimited scaling
        base_concurrency: int = 10,
        retry_delays: List[float] = None,
        adaptive_chunk_size: bool = True
    ):
        """
        Initialize upload queue manager.
        
        Args:
            min_workers: Minimum number of worker threads
            max_workers: Maximum number of worker threads (None = unlimited, scales based on system)
            base_concurrency: Base concurrency for small batches
            retry_delays: List of retry delays in seconds (exponential backoff)
            adaptive_chunk_size: Whether to use adaptive chunk sizing for very large batches
        """
        self.min_workers = min_workers
        self.max_workers = max_workers  # None means unlimited scaling
        self.base_concurrency = base_concurrency
        self.adaptive_chunk_size = adaptive_chunk_size
        
        # Retry delays with exponential backoff: [1s, 2s, 4s, 8s]
        self.retry_delays = retry_delays or [1.0, 2.0, 4.0, 8.0]
        
        # Queue for pending tasks
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # Dictionary to track all tasks
        self.tasks: Dict[str, UploadTask] = {}
        
        # Worker pool
        self.workers: List[asyncio.Task] = []
        self.worker_count = 0
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed": 0,
            "failed": 0,
            "duplicates": 0,
            "retries": 0
        }
    
    def calculate_worker_count(self, queue_size: int) -> int:
        """
        Calculate optimal worker count based on queue size.
        Scales dynamically: more workers for larger queues.
        No upper limit - scales infinitely based on queue size.
        """
        if queue_size == 0:
            return self.min_workers
        
        # Adaptive scaling formula: base + log(queue_size) * multiplier
        # This allows scaling to millions/billions without linear growth
        # For very large queues, use logarithmic scaling to prevent resource exhaustion
        import math
        
        if queue_size < 100:
            # Small batches: linear scaling
            calculated = self.base_concurrency + (queue_size // 20)
        elif queue_size < 10000:
            # Medium batches: moderate scaling
            calculated = self.base_concurrency + int(math.log10(queue_size) * 10)
        else:
            # Large batches (10k+): logarithmic scaling
            # Prevents excessive worker creation for millions/billions of files
            calculated = self.base_concurrency + int(math.log10(queue_size) * 15)
        
        # Apply max_workers limit if set, otherwise scale freely
        if self.max_workers is not None:
            return max(self.min_workers, min(self.max_workers, calculated))
        else:
            # Unlimited scaling, but cap at reasonable system limit (1000 workers)
            # This prevents resource exhaustion while allowing massive scale
            return max(self.min_workers, min(calculated, 1000))
    
    async def add_task(
        self,
        task_id: str,
        file: Any,
        filename: str,
        folder: Optional[str] = None,
        checksum: Optional[str] = None,
        max_retries: int = 3
    ) -> UploadTask:
        """Add a task to the upload queue."""
        task = UploadTask(
            task_id=task_id,
            file=file,
            filename=filename,
            folder=folder,
            checksum=checksum,
            max_retries=max_retries
        )
        self.tasks[task_id] = task
        await self.task_queue.put(task)
        self.stats["total_tasks"] += 1
        logger.debug(f"Added task {task_id} to queue: {filename} (queue size: {self.task_queue.qsize()})")
        return task
    
    async def start_workers(self, processor: Callable):
        """Start worker pool with dynamic scaling."""
        if self.is_running:
            logger.warning("Workers already running, skipping start")
            return
        
        logger.info(f"Starting worker pool with {self.min_workers} initial workers")
        self.is_running = True
        
        # Start initial workers
        initial_workers = self.min_workers
        for i in range(initial_workers):
            worker = asyncio.create_task(self._worker(processor))
            self.workers.append(worker)
            self.worker_count += 1
            logger.debug(f"Started worker {i+1}/{initial_workers}")
        
        # Start dynamic scaling task
        asyncio.create_task(self._scale_workers(processor))
        logger.info(f"Worker pool started with {self.worker_count} workers")
    
    async def _scale_workers(self, processor: Callable):
        """Dynamically scale workers based on queue size."""
        logger.debug("Worker scaling task started")
        while self.is_running:
            await asyncio.sleep(2)  # Check every 2 seconds
            
            queue_size = self.task_queue.qsize()
            optimal_workers = self.calculate_worker_count(queue_size)
            
            # Add workers if needed
            max_allowed = self.max_workers if self.max_workers is not None else 1000
            workers_added = 0
            while self.worker_count < optimal_workers and self.worker_count < max_allowed:
                worker = asyncio.create_task(self._worker(processor))
                self.workers.append(worker)
                self.worker_count += 1
                workers_added += 1
            
            if workers_added > 0:
                logger.info(f"Scaled up: Added {workers_added} workers (total: {self.worker_count}, queue: {queue_size})")
            
            # Remove excess workers (gracefully, let them finish current task)
            # We don't kill workers immediately, they'll finish naturally
    
    async def _worker(self, processor: Callable):
        """Worker coroutine that processes tasks from queue."""
        worker_id = id(asyncio.current_task())
        logger.debug(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get task with timeout to allow checking is_running
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # If queue is empty and we have too many workers, exit
                    if self.task_queue.qsize() == 0 and self.worker_count > self.min_workers:
                        logger.debug(f"Worker {worker_id} exiting (queue empty, excess workers)")
                        break
                    continue
                
                logger.debug(f"Worker {worker_id} processing task {task.task_id}: {task.filename}")
                # Process task
                await self._process_task(task, processor)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        # Worker is done
        self.worker_count -= 1
        logger.debug(f"Worker {worker_id} stopped (remaining workers: {self.worker_count})")
    
    async def _process_task(self, task: UploadTask, processor: Callable):
        """Process a single upload task with retry logic."""
        task.mark_processing()
        logger.debug(f"Processing task {task.task_id}: {task.filename} (attempt {task.retry_count + 1})")
        
        while True:
            try:
                # Process the task (processor should return a dict with status)
                result = await processor(task)
                
                # Check result status
                if result.get("status") == "success":
                    task.mark_success(result)
                    self.stats["completed"] += 1
                    logger.info(f"Task {task.task_id} completed successfully: {task.filename}")
                    break
                elif result.get("status") == "duplicate":
                    task.mark_duplicate(result.get("existing_document", {}))
                    self.stats["duplicates"] += 1
                    logger.info(f"Task {task.task_id} skipped (duplicate): {task.filename}")
                    break
                elif result.get("status") == "error":
                    # Task failed
                    error_msg = result.get("error", "Unknown error")
                    if task.can_retry():
                        # Retry with exponential backoff
                        task.mark_retrying()
                        self.stats["retries"] += 1
                        delay = self.retry_delays[min(task.retry_count - 1, len(self.retry_delays) - 1)]
                        logger.warning(f"Task {task.task_id} failed, retrying in {delay}s (attempt {task.retry_count + 1}/{task.max_retries}): {error_msg}")
                        await asyncio.sleep(delay)
                        continue  # Retry
                    else:
                        # Max retries reached
                        task.mark_failed(error_msg)
                        self.stats["failed"] += 1
                        logger.error(f"Task {task.task_id} failed after {task.retry_count} retries: {task.filename} - {error_msg}")
                        break
                else:
                    # Unknown status
                    error_msg = f"Unknown status: {result.get('status')}"
                    task.mark_failed(error_msg)
                    self.stats["failed"] += 1
                    logger.error(f"Task {task.task_id} failed with unknown status: {error_msg}")
                    break
                        
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                if task.can_retry():
                    task.mark_retrying()
                    self.stats["retries"] += 1
                    delay = self.retry_delays[min(task.retry_count - 1, len(self.retry_delays) - 1)]
                    logger.warning(f"Task {task.task_id} exception, retrying in {delay}s: {error_msg}", exc_info=True)
                    await asyncio.sleep(delay)
                    continue  # Retry
                else:
                    task.mark_failed(error_msg)
                    self.stats["failed"] += 1
                    logger.error(f"Task {task.task_id} failed after {task.retry_count} retries: {task.filename} - {error_msg}", exc_info=True)
                    break
    
    async def wait_for_completion(self, timeout: Optional[float] = None) -> Dict:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None = no timeout)
        
        Returns:
            Dictionary with completion statistics
        """
        start_time = time.time()
        
        while True:
            # Check if all tasks are done
            pending = sum(1 for task in self.tasks.values() 
                         if task.status in [UploadStatus.PENDING, UploadStatus.PROCESSING, UploadStatus.RETRYING])
            
            if pending == 0:
                break
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                break
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        return self.get_stats()
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        return {
            **self.stats,
            "pending": sum(1 for t in self.tasks.values() if t.status == UploadStatus.PENDING),
            "processing": sum(1 for t in self.tasks.values() if t.status == UploadStatus.PROCESSING),
            "retrying": sum(1 for t in self.tasks.values() if t.status == UploadStatus.RETRYING),
            "queue_size": self.task_queue.qsize(),
            "worker_count": self.worker_count
        }
    
    def get_task(self, task_id: str) -> Optional[UploadTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[UploadTask]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    async def stop(self):
        """Stop all workers and clean up."""
        logger.info(f"Stopping worker pool ({self.worker_count} workers, {self.task_queue.qsize()} tasks in queue)")
        self.is_running = False
        
        # Wait for queue to empty
        await self.task_queue.join()
        logger.debug("Queue emptied, waiting for workers to finish")
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        self.worker_count = 0
        logger.info("Worker pool stopped")

