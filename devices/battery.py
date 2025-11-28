import asyncio
import json
import logging
import time

import machine
from board.board_application import BoardApplication, Facility
from configuration import Configuration
from ina3221 import *
from machine import Pin

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class BatteryApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'battery', use_mqtt=True)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        bus  = machine.SoftI2C(scl=Pin(3), sda=Pin(2), freq=400000)
        # INA3221.IS_FULL_API = False
        ina = INA3221(bus, i2c_addr=0x40)
        if INA3221.IS_FULL_API:
            ina.update(reg=C_REG_CONFIG,
                       mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
                       value=C_AVERAGING_128_SAMPLES | C_VBUS_CONV_TIME_8MS | C_SHUNT_CONV_TIME_8MS | C_MODE_SHUNT_AND_BUS_CONTINOUS)

        self.ina = Facility("electricity", ina, {
            'voltage': 0.0,
            'current': 0.0,
            'active_power': 0.0,
            'active_energy': 0.0,
            'power_factor': 1.0,
        })
        self.channel = 1
        self.ina.endpoint.enable_channel(self.channel)

    def read(self, to_json = True):
        result = self.ina.to_dict()
        return json.dumps(result) if to_json else result

    async def ina_task(self):
        start_time = time.ticks_us()
        size = 60
        size_time = 60_000_000  # 60 seconds
        voltage = [0] * size
        current = [0] * size

        index = 0
        while not self.exit:
            await asyncio.sleep_ms(1_000)

            voltage[index] = self.ina.endpoint.bus_voltage(self.channel) + self.ina.endpoint.shunt_voltage(self.channel)
            current[index] = self.ina.endpoint.current(self.channel)
            if index >= size - 1 or time.ticks_diff(time.ticks_us(), start_time) > size_time:
                avg_voltage = sum(voltage) / (index + 1)
                avg_current = sum(current) / (index + 1)
                self.ina.value['voltage'] = avg_voltage
                self.ina.value['current'] = avg_current
                self.ina.value['active_power'] = avg_voltage * avg_current
                self.ina.value = self.ina.value  # trigger set
                start_time = time.ticks_us()
                index = 0
                await self.publish(self.topic_data, self.read(to_json=False), True)
            else:
                index += 1

    async def start(self):
        await super().start()
        self.ina.task = asyncio.create_task(self.ina_task())

    def deinit(self):
        super().deinit()
        self.ina.task.cancel()


if __name__ == "__main__":
    BatteryApplication().run()
