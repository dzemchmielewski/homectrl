import asyncio
import json
import logging
import time

from board.board_application import BoardApplication
from toolbox.pinio import PinIO
from configuration import Configuration
from machine import Pin, SoftI2C
from ac_voltage import ACVoltage

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class SocketApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'socket')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        self.relay = PinIO(0, False)
        self.ads = ACVoltage(SoftI2C(scl=Pin(2), sda=Pin(1)), 21, 0)
        self.current = 0
        self.read_current = None
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
            "relay": self.relay.last_value,
            "current_transient": self.current,
            "read_current": self.read_current,
            "active_power": self.current * 239,
            "control": self.control
        }
        return json.dumps(result) if to_json else result

    async def current_task(self):
        while not self.exit:
            self.current = self.ads.read() / 100
            self.read_current = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            await asyncio.sleep_ms(200)
            # print(f"Voltage: {v:.4f}mV, amps: {amps:.4f}")

    async def work_task(self):
        while not self.exit:
            if self.control['mode'] == "auto":
                # TODO: set relay by darkness
                relay = 0
            elif self.control['mode'] == "on":
                relay = 1
            elif self.control['mode'] == "off":
                relay = 0
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            if self.relay.last_value != relay:
                self.relay.set(relay)
                await self.publish(self.topic_data, self.read(to_json=False), True)

            await asyncio.sleep_ms(200)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work_task())
        self._current_task = asyncio.create_task(self.current_task())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()
        self._current_task.cancel()

