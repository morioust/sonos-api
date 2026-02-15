import asyncio
import functools
import logging
from collections.abc import Callable
from typing import TypeVar

from soco.exceptions import SoCoException

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_soco(max_retries: int = 1, delay: float = 1.0) -> Callable:
    """Retry decorator for transient SoCo/network failures.

    Only retries on SoCoException and ConnectionError.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (SoCoException, ConnectionError, TimeoutError, OSError) as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        logger.warning(
                            "Retrying %s (attempt %d/%d): %s",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            exc,
                        )
                        await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
