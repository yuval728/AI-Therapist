import anyio
from typing import Callable, Any
from litellm import completion
from loguru import logger
from src.config import get_settings

settings = get_settings()

async def run_completion_safely(func: Callable[..., Any], *args, **kwargs) -> Any:
	"""Run blocking LiteLLM completion in a thread with basic retry."""
	retries = 2
	delay = 0.5
	for attempt in range(retries + 1):
		try:
			return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs), cancellable=True)
		except Exception as e:  # noqa
			logger.warning(f"completion_error attempt={attempt} error={e}")
			if attempt == retries:
				raise
			await anyio.sleep(delay * (attempt + 1))

async def async_completion(**kwargs):
	return await run_completion_safely(completion, **kwargs)
