import time
import asyncio
import json
import logging
from board.board_application import BoardApplication, Facility
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

        self.conditions_reader = BMP_AHT.from_pins(9, 5, calibrate_pressure=-3.6)
        self.read_conditions = None
        self.conditions = (None, None, None)

        self.darkness = Facility("darkness",
                                 endpoint=DarknessSensor.from_analog_pin(2, queue_size=90, voltage_threshold=2.7))
        self.voltage = Facility("voltage")
        self.voltage_momentary = Facility("voltage_momentary")

        self.light = Facility("light", PinIO(0, set_initial=False), value=False, register_access=False)
        self.light_floating_time = None

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
        result = (
                self.light.to_dict()
                | self.darkness.to_dict()
                | self.voltage.to_dict()
                | self.voltage_momentary.to_dict()
                | {
                    "read_presence": self.read_presence,
                    "presence":  self.presence,
                    "read_conditions": self.read_conditions,
                    "temperature": self.conditions[0],
                    "pressure": self.conditions[1],
                    "humidity": self.conditions[2],
                })
        return json.dumps(result) if to_json else result


    def determine_light(self, presence):

        if self.control['mode'] == 'on':
            return True

        elif self.control['mode'] == 'off':
            return False

        elif self.control['mode'] == 'auto':
            new_light = self.darkness.value and presence

            if not self.light.value and new_light:
                # Turn on the light immediately, if darkness and presence
                self.light_floating_time = None
                return True

            elif self.light.value == new_light:
                self.light_floating_time = None
                return self.light.value

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

            if (presence, light) != (self.presence, self.light.value):
                self.presence = presence
                self.light.value = light
                self.light.endpoint.set(self.light.value)
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
            new_darkness, mean_voltage, new_voltage_momentary = self.darkness.endpoint.read_analog()
            new_voltage = round(mean_voltage, 1)
            if new_voltage_momentary != self.voltage_momentary.value:
                self.voltage_momentary.value = new_voltage_momentary
            if (new_voltage, new_darkness) != (self.voltage.value, self.darkness.value):
                self.voltage.value = new_voltage
                self.darkness.value = new_darkness
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(5)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work_task())
        self._conditions_task = asyncio.create_task(self.conditions_task())
        self.darkness.task = asyncio.create_task(self.darkness_task())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()
        self._conditions_task.cancel()
        self.darkness.task.cancel()

