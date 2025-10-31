"""Batch processing utilities for performance optimization."""

import asyncio
from collections.abc import Callable
from typing import TypeVar

from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class BatchProcessor:
    """Batch processor for aggregating and processing items in batches."""

    def __init__(
        self,
        batch_size: int = 10,
        max_wait_seconds: float = 0.5,
        processor: Callable[[list[T]], list[R]] | None = None,
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Maximum number of items per batch
            max_wait_seconds: Maximum time to wait before processing partial batch
            processor: Async function to process batch (receives list, returns list)
        """
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds
        self.processor = processor
        self._queue: list[tuple[T, asyncio.Future]] = []
        self._lock = asyncio.Lock()
        self._processing = False
        self._timer_task: asyncio.Task | None = None

    async def add(self, item: T) -> R:
        """
        Add item to batch for processing.

        Returns the processed result for this item.
        """
        logger.debug(f"[add] Starting add for item: {item}")
        future: asyncio.Future = asyncio.Future()
        should_process = False

        logger.debug(f"[add] Acquiring lock for item: {item}")
        async with self._lock:
            logger.debug(
                f"[add] Lock acquired for item: {item}, current queue size: {len(self._queue)}"
            )
            self._queue.append((item, future))
            logger.debug(f"[add] Item {item} added to queue, new queue size: {len(self._queue)}")

            # Cancel existing timer if running
            if self._timer_task and not self._timer_task.done():
                logger.debug(f"[add] Cancelling existing timer for item: {item}")
                self._timer_task.cancel()
                self._timer_task = None

            # Check if we should process immediately
            if len(self._queue) >= self.batch_size and not self._processing:
                logger.debug(
                    f"[add] Queue size {len(self._queue)} >= batch_size {self.batch_size}, will process batch for item: {item}"
                )
                should_process = True
            elif not self._processing:
                # Start timer for partial batch
                logger.debug(f"[add] Starting timer for partial batch, item: {item}")
                self._timer_task = asyncio.create_task(self._timer())
            else:
                logger.debug(f"[add] Already processing, item {item} will wait")

        logger.debug(f"[add] Lock released for item: {item}, should_process: {should_process}")

        # Process outside the lock to avoid deadlock
        if should_process:
            logger.debug(f"[add] Calling _process_batch for item: {item}")
            await self._process_batch()

        logger.debug(f"[add] Awaiting future for item: {item}")
        result = await future
        logger.debug(f"[add] Future resolved for item: {item}, result: {result}")
        return result

    async def _timer(self) -> None:
        """Timer to process partial batch after max_wait_seconds."""
        logger.debug(f"[_timer] Timer started, will wait {self.max_wait_seconds}s")
        try:
            await asyncio.sleep(self.max_wait_seconds)
        except asyncio.CancelledError:
            # Timer was cancelled before sleep completed
            logger.debug("[_timer] Timer was cancelled during sleep")
            return

        # If we get here, timer expired - process the batch
        logger.debug("[_timer] Timer expired, calling _process_batch")
        try:
            await self._process_batch()
            logger.debug("[_timer] Timer completed successfully")
        except Exception as e:
            logger.error(f"[_timer] Error in timer processing: {e}", exc_info=True)

    async def _process_batch(self) -> None:
        """Process current batch of items."""
        logger.debug("[_process_batch] Starting batch processing")
        async with self._lock:
            logger.debug(
                f"[_process_batch] Lock acquired, queue size: {len(self._queue)}, processing: {self._processing}"
            )
            if self._processing or not self._queue:
                logger.debug(
                    f"[_process_batch] Skipping - processing: {self._processing}, queue empty: {not self._queue}"
                )
                return

            self._processing = True
            batch = self._queue[: self.batch_size]
            self._queue = self._queue[self.batch_size :]
            logger.debug(
                f"[_process_batch] Extracted batch of {len(batch)} items, remaining queue: {len(self._queue)}"
            )

            # Don't cancel timer here - let it complete naturally to avoid cancelling ourselves
            # The timer will check if queue is empty and exit gracefully

            # Restart timer if there are remaining items and no timer is running
            if self._queue and (not self._timer_task or self._timer_task.done()):
                logger.debug(
                    f"[_process_batch] Restarting timer for {len(self._queue)} remaining items"
                )
                self._timer_task = asyncio.create_task(self._timer())

        logger.debug(f"[_process_batch] Lock released, processing batch of {len(batch)} items")
        try:
            items = [item for item, _ in batch]
            futures = [future for _, future in batch]
            logger.debug(
                f"[_process_batch] Extracted {len(items)} items and {len(futures)} futures"
            )

            if self.processor:
                logger.debug(f"[_process_batch] Calling processor with {len(items)} items")
                try:
                    results = await self.processor(items)
                    logger.debug(f"[_process_batch] Processor returned {len(results)} results")
                except Exception as proc_ex:
                    logger.error(
                        f"[_process_batch] Processor raised exception: {proc_ex}", exc_info=True
                    )
                    raise

                if len(results) != len(items):
                    raise ValueError(
                        f"Processor returned {len(results)} results for {len(items)} items"
                    )

                logger.debug(f"[_process_batch] Setting results on {len(futures)} futures")
                for i, (future, result) in enumerate(zip(futures, results, strict=True)):
                    if not future.done():
                        logger.debug(f"[_process_batch] Setting result {result} on future {i}")
                        future.set_result(result)
                    else:
                        logger.debug(f"[_process_batch] Future {i} already done")
            else:
                # No processor, just return items as-is
                logger.debug("[_process_batch] No processor, returning items as-is")
                for future, item in zip(futures, items, strict=True):
                    if not future.done():
                        future.set_result(item)

            logger.debug("[_process_batch] All futures resolved successfully")

        except Exception as e:
            logger.error(f"[_process_batch] Error processing batch: {e}")
            # Set exception on all futures
            for _, future in batch:
                if not future.done():
                    future.set_exception(e)
        finally:
            logger.debug("[_process_batch] Acquiring lock to reset processing flag")
            async with self._lock:
                self._processing = False
                logger.debug(
                    f"[_process_batch] Processing flag reset to False, queue size: {len(self._queue)}"
                )

                # If there are items in queue, ensure they will be processed
                if self._queue:
                    queue_size = len(self._queue)
                    has_timer = self._timer_task and not self._timer_task.done()

                    if queue_size >= self.batch_size:
                        # Cancel timer and process immediately
                        if has_timer:
                            logger.debug(
                                "[_process_batch] Cancelling timer, processing full batch immediately"
                            )
                            self._timer_task.cancel()
                            self._timer_task = None
                        logger.debug(f"[_process_batch] Creating task for {queue_size} items")
                        asyncio.create_task(self._process_batch())
                    elif not has_timer:
                        # Start timer for partial batch only if no timer exists
                        logger.debug(
                            f"[_process_batch] Starting timer for {queue_size} remaining items"
                        )
                        self._timer_task = asyncio.create_task(self._timer())
                    else:
                        logger.debug(
                            f"[_process_batch] Timer already running for {queue_size} items"
                        )

    async def flush(self) -> None:
        """Process all remaining items in queue."""
        while True:
            async with self._lock:
                if not self._queue:
                    break
            await self._process_batch()


async def batch_process_items(
    items: list[T],
    processor: Callable[[list[T]], list[R]],
    batch_size: int = 10,
    max_concurrency: int = 5,
) -> list[R]:
    """
    Process items in batches with concurrency control.

    Args:
        items: List of items to process
        processor: Async function to process each batch
        batch_size: Number of items per batch
        max_concurrency: Maximum number of concurrent batch operations

    Returns:
        List of processed results in same order as input items
    """
    if not items:
        return []

    # Split into batches
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_batch_with_semaphore(batch: list[T]) -> list[R]:
        async with semaphore:
            return await processor(batch)

    # Process batches concurrently
    tasks = [process_batch_with_semaphore(batch) for batch in batches]
    batch_results = await asyncio.gather(*tasks)

    # Flatten results
    results: list[R] = []
    for batch_result in batch_results:
        results.extend(batch_result)

    return results


async def parallel_map(
    items: list[T],
    func: Callable[[T], R],
    max_concurrency: int = 10,
) -> list[R]:
    """
    Apply async function to items in parallel with concurrency control.

    Args:
        items: List of items to process
        func: Async function to apply to each item
        max_concurrency: Maximum number of concurrent operations

    Returns:
        List of results in same order as input items
    """
    if not items:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_with_semaphore(item: T) -> R:
        async with semaphore:
            return await func(item)

    tasks = [process_with_semaphore(item) for item in items]
    return await asyncio.gather(*tasks)
