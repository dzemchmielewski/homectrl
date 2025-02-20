import time
import asyncio
import json
import logging
from board.board_application import BoardApplication
from configuration import Configuration
from machine import Pin

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class WardrobeApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'wardrobe')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        self.door_sensor = Pin(3, Pin.IN)
        self.light_pin = Pin(4, Pin.OUT)
        self.read_light = None
        self.light = None
        self.capabilities = {
            "controls": [
                {
                    "name": "mode",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "auto", "off"]
                    }
                }
            ]}
        self.control = {
            'mode': 'auto'
        }

    def read(self, to_json = True):
        result = {
            "read_light": self.read_light,
            "light":  self.light,
            "control": self.control
        }
        return json.dumps(result) if to_json else result

    async def work(self):
        while not self.exit:
            if self.control['mode'] == "auto":
                light = self.door_sensor.value()
            elif self.control['mode'] == "on":
                light = 1
            elif self.control['mode'] == "off":
                light = 0
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            self.read_light = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if light != self.light:
                self.light = light
                self.light_pin.value(light)
                await self.publish(self.topic_data, self.read(to_json=False), True)

            await asyncio.sleep_ms(200)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()

