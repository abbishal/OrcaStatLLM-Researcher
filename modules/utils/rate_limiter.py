import time
import asyncio
import logging

logger = logging.getLogger("OrcaStatLLM-Scientist")

class RateLimitHandler:
    def __init__(self, max_retries=3, retry_delay=5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.service_last_call = {
            "google_cse": 0,
            "openverse": 0,
            "gemini": 0,
            "duckduckgo": 0,
            "wikipedia": 0,
            "unsplash": 0,
            "arxiv": 0,
            "brave": 0
        }
        self.service_min_interval = {
            "google_cse": 1,
            "openverse": 1,
            "gemini": 0.2,
            "duckduckgo": 2,
            "wikipedia": 0.5,
            "unsplash": 1.5,
            "arxiv": 3,
            "brave": 3
        }
    
    def should_wait(self, service):
        now = time.time()
        last_call = self.service_last_call.get(service, 0)
        min_interval = self.service_min_interval.get(service, 0)
        
        if now - last_call < min_interval:
            return min_interval - (now - last_call)
        return 0
    
    def update_last_call(self, service):
        self.service_last_call[service] = time.time()
    
    async def wait_if_needed(self, service):
        wait_time = self.should_wait(service)
        if (wait_time > 0):
            await asyncio.sleep(wait_time)
        self.update_last_call(service)

    async def handle_rate_limit(self, func_name, retry_count, max_retries=3):
        if retry_count >= max_retries:
            return False
            
        backoff_time = retry_count * 5
        logger.info(f"Rate limit hit. Retrying {func_name} in {backoff_time}s (attempt {retry_count+1}/{max_retries})")
        await asyncio.sleep(backoff_time)
        return True

