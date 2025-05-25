import time
from functools import wraps
from datetime import datetime, timedelta
from django.core.cache import cache
import logging
from queue import Queue
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_requests=5, time_window=60, cache_prefix='rate_limit', queue_size=100):
        self.max_requests = max_requests
        self.time_window = time_window
        self.cache_prefix = cache_prefix
        self.request_queue = Queue(maxsize=queue_size)
        self.lock = Lock()

    def get_cache_key(self, key):
        return f"{self.cache_prefix}_{key}"

    def is_rate_limited(self, key):
        with self.lock:
            cache_key = self.get_cache_key(key)
            requests = cache.get(cache_key, [])
            now = datetime.now()

            # Remove old requests outside the time window
            requests = [req for req in requests 
                       if now - req <= timedelta(seconds=self.time_window)]

            # Check if we're over the limit
            if len(requests) >= self.max_requests:
                # Add request to queue if rate limited
                try:
                    self.request_queue.put_nowait((key, now))
                    logger.info(f"Request for {key} queued. Queue size: {self.request_queue.qsize()}")
                except Queue.Full:
                    logger.warning(f"Request queue full for {key}")
                return True

            # Process queued requests if available
            while not self.request_queue.empty() and len(requests) < self.max_requests:
                try:
                    queued_key, queued_time = self.request_queue.get_nowait()
                    if queued_key == key:
                        requests.append(now)
                        logger.info(f"Processed queued request for {key}")
                except Queue.Empty:
                    break

            # Add current request timestamp
            if len(requests) < self.max_requests:
                requests.append(now)
                cache.set(cache_key, requests, self.time_window)
                return False

            return True

def retry_with_backoff(max_retries=3, initial_delay=1, max_delay=60, exponential_base=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            retries = 0

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if 'Too Many Requests' not in str(e):
                        raise e

                    retries += 1
                    if retries == max_retries:
                        raise e

                    sleep_time = min(delay * (exponential_base ** (retries - 1)), max_delay)
                    logger.warning(f"Rate limited. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)

            return func(*args, **kwargs)
        return wrapper
    return decorator

# Global rate limiter instance for stock API
stock_rate_limiter = RateLimiter(max_requests=5, time_window=60, cache_prefix='stock_api')