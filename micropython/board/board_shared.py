import asyncio
import logging

class DataEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self.data = None

    def clear(self):
        self.data = None
        super().clear()

    def set(self, data = None):
        self.data = data
        super().set()


class Exit:
    VALUE = False

    @staticmethod
    def is_exit():
        return Exit.VALUE

    @staticmethod
    def go():
        Exit.VALUE = True

    @staticmethod
    def init():
        Exit.VALUE = False


class Named:
    def __init__(self, name: str):
        self.name = name
        self.log = logging.getLogger(self.name)
        self.log.info(f"Initializing {self.name} - {self}")


class Exitable:

    def __init__(self):
        self.exit = False
        self._exit_task = asyncio.create_task(self._exit())

    def deinit(self):
        pass

    async def _exit(self):
        while not Exit.is_exit():
            await asyncio.sleep_ms(100)
        try:
            self.log.info(f"Exit {self}")
        except AttributeError:
            logging.info(f"Exit {self}")
        self.exit = True
        self.deinit()


class EventEmitter(Named):
    def __init__(self, name: str):
        if not hasattr(self, 'name'):
            Named.__init__(self, name)
        self.events = {}

    def register_recipient(self, recipient: str) -> DataEvent:
        self.events[recipient] = DataEvent()
        return self.events[recipient]

    def emit(self, data: dict):
        if not data.get('sender'):
            data['sender'] = self.name
        self.log.debug(f"EMIT: {data}")
        if (event := self.events.get(data['recipient'])) is not None:
            if event.data is not None:
                event.data.append(data)
            else:
                event.set([data])
        else:
            raise Exception(f"{self.__class__} is trying to emit data event: {data}, but no recipient is registered.")


class EventConsumer(Exitable, Named):
    def __init__(self, name: str):
        if not hasattr(self, 'exit'):
            Exitable.__init__(self)
        if not hasattr(self, 'name'):
            Named.__init__(self, name)
        self._listener_tasks = []

    def listen_to(self, emitter: EventEmitter):
        self._listener_tasks.append(asyncio.create_task(self._listener(emitter.register_recipient(self.name))))

    async def consume(self, event: dict):
        return True

    async def _listener(self, event: DataEvent):
        while not self.exit:
            await event.wait()
            for data in event.data:
                # self.log.debug(f"RECV: {data}")
                await self.consume(data)
            event.clear()

    def deinit(self):
        super().deinit()
        for task in self._listener_tasks:
            task.cancel()

