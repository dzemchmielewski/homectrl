import time
import asyncio
import json
import logging
from board.board_application import BoardApplication
from configuration import Configuration
from machine import UART
from toolbox.bmp_aht import BMP_AHT
from toolbox.ld2410 import LD2410
from toolbox.radar_control import RadarControl
from toolbox.pinio import PinIO

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class ToiletApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'toilet')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.presence_reader = PinIO(3)
        self.conditions_reader = BMP_AHT.from_pins(2, 5)

        self.read_presence = None
        self.presence = None

        self.read_conditions = None
        self.conditions = (None, None, None)

        self.light = False
        self.light_floating_time = None

        self.light_switch = PinIO(4, set_initial=self.light)

        uart = UART(1, baudrate=256000, bits=8, parity=None, stop=1, tx=0, rx=1, timeout=1)
        self.radar = LD2410(uart)
        self.radar_control = RadarControl(self.radar)

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
            "read_presence": self.read_presence,
            "presence":  self.presence,
            "read_conditions": self.read_conditions,
            "temperature": self.conditions[0],
            "pressure": self.conditions[1],
            "humidity": self.conditions[2],
            "light": self.light
        }
        return json.dumps(result) if to_json else result


    def determine_light(self, presence):
        if self.control['mode'] == 'on':
            return True

        elif self.control['mode'] == 'off':
            return False

        elif self.control['mode'] == 'auto':
            if not self.light and presence:
                # Turn on the light immediately, if darkness and presence
                self.light_floating_time = None
                return True

            elif self.light == presence:
                self.light_floating_time = None
                return self.light

            else:
                # The last case - the light is on and can be turned off
                # however, not immediately
                if not self.light_floating_time:
                    self.light_floating_time = time.ticks_ms()
                    return True

                else:
                    if time.ticks_ms() - self.light_floating_time > 2 * 1_000:
                        self.light_floating_time = None
                        return False
                    else:
                        return True

    async def work_task(self):
        while not self.exit:
            self.read_presence = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            presence = self.presence_reader.get()
            light = self.determine_light(presence)

            if (presence, light) != (self.presence, self.light):
                self.presence = presence
                self.light = light
                self.light_switch.set(self.light)
                await self.publish(self.topic_data, self.read(False), True)

            await asyncio.sleep_ms(50)

    async def conditions_task(self):
        while not self.exit:
            readings = (self.conditions_reader.temperature, self.conditions_reader.pressure, self.conditions_reader.humidity)
            self.read_conditions = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if readings != self.conditions:
                self.conditions = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work_task())
        self._conditions_task = asyncio.create_task(self.conditions_task())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()
        self._conditions_task.cancel()

