import time
import asyncio
import json
import logging
from board.board_application import BoardApplication
from board.board_shared import Utils as util
from configuration import Configuration
from machine import UART
from toolbox.bmp_aht import BMP_AHT
from toolbox.ld2410 import LD2410
from toolbox.radar_control import RadarControl
from toolbox.pinio import PinIO
from toolbox.darkness import DarknessSensor

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class KitchenApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'kitchen')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.presence_reader = PinIO(10)
        self.read_presence = None
        self.presence = None

        self.conditions_reader = BMP_AHT.from_pins(9, 5)
        self.read_conditions = None
        self.conditions = (None, None, None)

        self.darkness_sensor = DarknessSensor.from_analog_pin(2, queue_size=90, voltage_threshold=2.7)
        self.read_darkness = None
        self.darkness = None
        self.darkness_voltage = None
        self.darkness_voltage_momentary = None

        self.light = False
        self.light_floating_time = None
        self.light_switch = PinIO(0, set_initial=self.light)

        self.radar = LD2410(UART(1, baudrate=256000, bits=8, parity=None, stop=1, tx=7, rx=6, timeout=1))
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
            "light": self.light,
            "read_presence": self.read_presence,
            "presence":  self.presence,
            "read_conditions": self.read_conditions,
            "temperature": self.conditions[0],
            "pressure": self.conditions[1],
            "humidity": self.conditions[2],
            "darkness": self.darkness,
            "voltage": self.darkness_voltage,
            "voltage_momentary": self.darkness_voltage_momentary,
            "read_darkness": self.read_darkness
        }
        return json.dumps(result) if to_json else result


    def determine_light(self, presence):

        if self.control['mode'] == 'on':
            return True

        elif self.control['mode'] == 'off':
            return False

        elif self.control['mode'] == 'auto':
            new_light = self.darkness and presence

            if not self.light and new_light:
                # Turn on the light immediately, if darkness and presence
                self.light_floating_time = None
                return True

            elif self.light == new_light:
                self.light_floating_time = None
                return self.light

            else:
                # The last case - the light is on and can be turned off
                # however, not immediately
                if not self.light_floating_time:
                    self.light_floating_time = time.ticks_ms()
                    return True

                else:
                    if time.ticks_ms() - self.light_floating_time > 20 * 1_000:
                        self.light_floating_time = None
                        return False
                    else:
                        return True

    async def work_task(self):
        while not self.exit:
            self.read_presence = util.time_str()
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
            self.read_conditions = util.time_str()
            if readings != self.conditions:
                self.conditions = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(60)

    async def darkness_task(self):
        while not self.exit:
            darkness, mean_voltage, self.darkness_voltage_momentary = self.darkness_sensor.read_analog()
            self.read_darkness = util.time_str()
            voltage = round(mean_voltage, 1)
            if (voltage, darkness) != (self.darkness_voltage, self.darkness):
                self.darkness_voltage = voltage
                self.darkness = darkness
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(5)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work_task())
        self._conditions_task = asyncio.create_task(self.conditions_task())
        self._darkness_task = asyncio.create_task(self.darkness_task())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()
        self._conditions_task.cancel()
        self._darkness_task.cancel()

