import asyncio
import functools
import logging
import inspect
from typing import Optional, Callable

from backend.tools import MQTTClient

def noexception(_fn: Optional[Callable] = None, *, logger: Optional[logging.Logger] = None):
    """Decorator usable as @noexception or @noexception(logger=...)."""
    logger = logger or logging.getLogger(__name__)

    def decorator(fn: Callable):
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    logger.error("Job %s failed: %s", fn.__qualname__, repr(e))
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    logger.error("Job %s failed: %s", fn.__qualname__, repr(e))
            return sync_wrapper

    # If _fn is provided, the decorator was used without args: @noexception
    if _fn is not None and callable(_fn):
        return decorator(_fn)

    # Otherwise used as @noexception(...) -> return the actual decorator
    return decorator


class OnAirService:
    def __init__(self):
        self.exit = False
        self.mqtt: MQTTClient = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        pass

    def on_message(self, client, userdata, msg):
        pass

    def on_disconnect(self, *args, **kwargs):
        pass

    def on_start(self):
        pass

    def on_stop(self):
        pass

    async def run(self) -> None:
        while not self.exit:
            await asyncio.sleep(1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

    logger = logging.getLogger('TestService')
    class TestService(OnAirService):

        def __init__(self):
            super().__init__()
            self.num = 0

        @noexception
        async def periodic_task(self):
            self.num += 1
            if self.num % 2 == 0:
                raise ValueError("Simulated error")
            logger.info("Periodic task executed")

        async def run(self) -> None:
            while not self.exit:
                await self.periodic_task()
                await asyncio.sleep(1)

    service = TestService()
    asyncio.run(service.run())
