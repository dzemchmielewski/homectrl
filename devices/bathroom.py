import asyncio
import json
import logging

import machine
from pzem import PZEM
from board.board_application import BoardApplication
from board.board_shared import Utils as util
from configuration import Configuration
from toolbox.bmp_aht import BMP_AHT

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class BathroomApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'bathroom')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.conditions_reader = BMP_AHT.from_pins(8, 9)
        self.read_conditions = None
        self.conditions = (None, None, None)

        self.pzem = PZEM(uart=machine.UART(1, baudrate=9600, tx=7, rx=6))
        self.electricity_summary = None,
        self.read_electricity = None
        self.electricity = {
            "voltage": None,
            "current": None,
            "active_power": None,
            "active_energy": None,
            "power_factor": None
        }


    def read(self, to_json = True):
        result = {
            "read_conditions": self.read_conditions,
            "temperature": self.conditions[0],
            "pressure": self.conditions[1],
            "humidity": self.conditions[2],
            "electricity_summary": self.electricity_summary,
            "electricity": self.electricity,
            "read_electricity": self.read_electricity
        }
        return json.dumps(result) if to_json else result

    async def electricity_task(self):
        while not self.exit:
            self.pzem.read()
            readings = {
                "voltage": self.pzem.getVoltage(),
                "current": round(self.pzem.getCurrent(), 3),
                # Active Power need to be greater than 0.4 - washing machine takes some small
                # power periodically what is messing reading history
                "active_power": round(self.pzem.getActivePower(), 1) if self.pzem.getActivePower() > 0.4 else 0,
                "active_energy": self.pzem.getActiveEnergy(),
                "power_factor": round(self.pzem.getPowerFactor(), 2) if self.pzem.getActivePower() > 0.4 else 0
            }
            self.read_electricity = util.time_str()
            self.electricity_summary = self.pzem.to_abbr_str()

            prev = self.electricity
            if ((readings["current"], readings["active_power"], readings["active_energy"], readings["power_factor"])
                    != (prev["current"], prev["active_power"], prev["active_energy"], prev["power_factor"])):
                self.electricity = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(2)


    async def conditions_task(self):
        while not self.exit:
            readings = (self.conditions_reader.temperature, self.conditions_reader.pressure, self.conditions_reader.humidity)
            self.read_conditions = util.time_str()
            if readings != self.conditions:
                self.conditions = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self._electricity_task = asyncio.create_task(self.electricity_task())
        self._conditions_task = asyncio.create_task(self.conditions_task())

    def deinit(self):
        super().deinit()
        self._electricity_task.cancel()
        self._conditions_task.cancel()

