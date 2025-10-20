import asyncio

from backend.tools import MQTTClient

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
