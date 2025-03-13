import time
import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, TypeVar, List, Optional, Tuple

T = TypeVar('T')
logger = logging.getLogger("OrcaStatLLM-Optimizer")

class PerformanceOptimizer:
    
    def __init__(self, max_concurrency: int = 5, cache_ttl: int = 3600):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.cache: Dict[str, Tuple[Any, float]] = {}  
        self.cache_ttl = cache_ttl
    
    async def run_with_cache(
        self, 
        func: Callable[..., Awaitable[T]], 
        cache_key: str,
        *args, 
        **kwargs
    ) -> T:

        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return result
        
        async with self.semaphore:
            logger.debug(f"Running {func.__name__} with key {cache_key}")
            result = await func(*args, **kwargs)
            self.cache[cache_key] = (result, time.time())
            return result
    
    async def run_concurrently(
        self, 
        tasks: List[Tuple[Callable[..., Awaitable[T]], Dict[str, Any]]], 
        return_exceptions: bool = True
    ) -> List[T]:
        async def run_task(func, kwargs):
            try:
                async with self.semaphore:
                    return await func(**kwargs)
            except Exception as e:
                if return_exceptions:
                    return e
                raise
        
        task_instances = [run_task(func, kwargs) for func, kwargs in tasks]
        results = await asyncio.gather(*task_instances, return_exceptions=return_exceptions)
        return results
    
    async def run_in_batches(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[T]], 
        batch_size: int = 3
    ) -> List[T]:
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            batch_tasks = [processor(item) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing item: {result}")
                    results.append(None)
                else:
                    results.append(result)
        
        return results
    
    def clear_cache(self, prefix: Optional[str] = None):
        if prefix:
            self.cache = {k: v for k, v in self.cache.items() if not k.startswith(prefix)}
        else:
            self.cache = {}