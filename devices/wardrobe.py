import asyncio
import json
import logging
from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class WardrobeApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'wardrobe')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        self.door = Facility("door", endpoint=Pin(3, Pin.IN), to_dict=lambda x : {})
        self.light = Facility("light", Pin(4, Pin.OUT), value=False, register_access=False)

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
        result = (
            self.door.to_dict()
            | self.light.to_dict()
            | {
                "control": self.control
            })
        return json.dumps(result) if to_json else result

    async def work(self):
        while not self.exit:
            if self.control['mode'] == "auto":
                light = self.door.endpoint.value()
            elif self.control['mode'] == "on":
                light = 1
            elif self.control['mode'] == "off":
                light = 0
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            if light != self.light.value:
                self.light.value = light
                self.light.endpoint.value(light)
                await self.publish(self.topic_data, self.read(to_json=False), True)

            await asyncio.sleep_ms(200)

    async def start(self):
        await super().start()
        self.light.task = asyncio.create_task(self.work())

    def deinit(self):
        super().deinit()
        self.light.task.cancel()

