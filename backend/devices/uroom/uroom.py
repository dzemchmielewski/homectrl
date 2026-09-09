#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/../env/bin/python" "$0" "$@"'

import logging
if __name__ == '__main__':
    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

import asyncio
import json
import smbus2 as smbus

from gpiozero import Button

from backend.modules.i2c import I2C
from backend.modules.mcp23017 import MCP23017, Config, Values
from backend.devices.attic.pi_application import PiApplication, Facility

logger = logging.getLogger("uroom")

# MCP23017:
# INTA -> GPIO 17
# INTB -> GPIO 27
# RESET (enable) -> GPIO 22

LIGHT_MAP = [
    ['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'],
    ['jroom', 'bathroom', 'backyard', 'bedroom', 'kitchen', 'B5', 'froom1', 'froom2']
]
# B2 - pull up issue

class URoomApplication(PiApplication):

    def __init__(self):
        super().__init__('uroom', use_mqtt=True)
        self.light_change = Facility("light_change", [Button(17), Button(27)])
        self.mcp = Facility("ceilinglight", MCP23017(0x27, I2C(smbus.SMBus(1)), enable_pin=22),
                            value={key: None for key in LIGHT_MAP[0]} | {key: None for key in LIGHT_MAP[1]})
        self.notify = Facility("notify")

    def read(self, to_json: bool = True) -> dict | str:
        result = self.mcp.to_dict()
        return json.dumps(result) if to_json else result

    async def notify_task(self):
        while not self.exit:
            await self.notify.event.wait()
            await self.publish(self.topic_data, self.read(to_json=False), retain=True)
            self.notify.event.clear()


    async def light_change_task(self):
        while not self.exit:
            await self.light_change.event.wait()
            value = self.mcp.endpoint.read_capture()
            if value != self.light_change.value:
                logger.debug(f"processing the change: {self.light_change.value.__repr__()} => {value.__repr__()}")
                xor = Values(
                    self.light_change.value.get(y=0) ^ value.get(y=0),
                    self.light_change.value.get(y=1) ^ value.get(y=1),
                    reverse=False
                )
                logger.debug(f"XOR: {xor.__repr__()}")
                for i in range(2):
                    for j in range(8):
                        room = LIGHT_MAP[i][j]
                        val = value.get(i, j)
                        if xor.get(i,j ) == 1:
                            logger.info(f"[CEIL LIGHT] {room} => {'OFF' if val == 1 else 'ON'}")
                        self.mcp.value[room] = not val
                self.light_change.value = value
                self.notify.event.set()
            self.light_change.event.clear()


    async def start(self):
        logger.info("starting...")
        self.notify.task = asyncio.create_task(self.notify_task())

        # Setup MCP:
        self.mcp.endpoint.config[Config.pullup].set(0b11111111, 0)
        self.mcp.endpoint.config[Config.pullup].set(0b11111111, 1)
        self.mcp.endpoint.config[Config.int_enable].set(0b11111111, 0)
        self.mcp.endpoint.config[Config.int_enable].set(0b11111111, 1)
        self.mcp.endpoint.push_config()

        loop = asyncio.get_running_loop()
        for i in range(2):
            self.light_change.endpoint[i].when_pressed = (lambda: loop.call_soon_threadsafe(self.light_change.event.set))

        self.light_change.task = asyncio.create_task(self.light_change_task())
        self.light_change.value = self.mcp.endpoint.read_output()


        logger.info(f"Initial value: {self.light_change.value.__repr__()}")
        for i in range(2):
            for j in range(8):
                self.mcp.value[LIGHT_MAP[i][j]] = not self.light_change.value.get(i, j)
        self.notify.event.set()
        logger.info(f"Initial value map: {self.mcp.value}")
        logger.info("started")

    def deinit(self):
        super().deinit()
        self.mcp.endpoint.deinit()
        self.light_change.task.cancel()
        [self.light_change.endpoint[i].close() for i in range(2)]
        logger.info("stopped")


if __name__ == "__main__":
    URoomApplication().run()
