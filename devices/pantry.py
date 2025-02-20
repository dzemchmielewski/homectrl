import time
import asyncio
import json
import logging
from board.board_application import BoardApplication
from configuration import Configuration
from machine import Pin
from toolbox.bmp_aht import BMP_AHT

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class PantryApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'pantry')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        self.door_sensor = Pin(3, Pin.IN)
        self.reader = BMP_AHT.from_pins(0, 1)

        self.read_light = None
        self.light = None

        self.read_sensor = None
        self.bmt_aht_readings = (None, None, None)

    def read(self, to_json = True):
        result = {
            "read_light": self.read_light,
            "light":  self.light,
            "temperature": self.bmt_aht_readings[0],
            "pressure": self.bmt_aht_readings[1],
            "humidity": self.bmt_aht_readings[2],
            "read_sensor": self.read_sensor
        }
        return json.dumps(result) if to_json else result

    async def work(self):
        while not self.exit:
            light = self.door_sensor.value()
            self.read_light = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if light != self.light:
                self.light = light
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep_ms(200)

    async def conditions(self):
        while not self.exit:
            readings = (self.reader.temperature, self.reader.pressure, self.reader.humidity)
            self.read_sensor = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            if readings != self.bmt_aht_readings:
                self.bmt_aht_readings = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self._work_task = asyncio.create_task(self.work())
        self._conditions_task = asyncio.create_task(self.conditions())

    def deinit(self):
        super().deinit()
        self._work_task.cancel()
        self._conditions_task.cancel()

