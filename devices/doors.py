import asyncio
import json
import logging

import time
from machine import Pin, UART, ADC

from board.board_application import BoardApplication, Facility
from configuration import Configuration
from pzem import PZEM
from rms import RMS
# from wavplayer import OneWavPlayer

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class DoorsApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'doors')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.electricity = Facility("electricity",
                                    PZEM(uart=UART(1, baudrate=9600, tx=1, rx=2)))
        self.doors = Facility("doors", Pin(4, Pin.IN, Pin.PULL_DOWN))
        adc = ADC(Pin(9, mode=Pin.IN))
        adc.atten(ADC.ATTN_11DB)
        self.bell = Facility("bell",
                             RMS(lambda: adc.read_uv(), max_samples_count=200, max_measure_time_us=50_000))
        # self.player = OneWavPlayer(
        #     id=0, sck_pin=Pin(11), ws_pin=Pin(13), sd_pin=Pin(12),
        #     ibuf=2_000, wav_file="example.wav",
        #     enable_pin=Pin(3, Pin.OUT))

        # self.mqtt_subscriptions[Configuration.TOPIC_ROOT.format("doors") + "/play"] = self.play_message

    def read(self, to_json = True):
        result = (self.doors.to_dict()
                  | self.bell.to_dict()
                  | self.electricity.to_dict()
                  # | {'play': self.player.isplaying()}
                  )
        return json.dumps(result) if to_json else result

    # def play_message(self, topic, msg, retained):
    #     self.player.play()

    async def bell_task(self):
        while not self.exit:
            new_value = self.bell.endpoint.get().rms > 200_000 # 0.2V
            if new_value != self.bell.value:
                self.bell.value = new_value
                # if self.bell.value and not self.player.isplaying():
                #     self.player.play()
                await self.publish(self.topic_data, self.read(to_json=False), True)
            await asyncio.sleep_ms(100)

    async def doors_task(self):
        while not self.exit:
            # 1 - no magnetic field - doors opened
            # 0 - magnetic field - doors closed
            new_value = bool(self.doors.endpoint.value())
            if new_value != self.doors.value:
                self.doors.value = new_value
                await self.publish(self.topic_data, self.read(to_json=False), True)
            await asyncio.sleep_ms(300)

    async def electricity_task(self):
        while not self.exit:
            # Sleep until current minute is divisible by 10
            (minute, second) = time.localtime()[4:6]
            seconds_this_hour = minute * 60 + second
            # i.e. number of seconds since the full hour is divisible by 600
            await asyncio.sleep(600-(seconds_this_hour % 600))

            self.electricity.endpoint.read()
            self.electricity.value = {
                "voltage": self.electricity.endpoint.getVoltage(),
                "current": round(self.electricity.endpoint.getCurrent(), 3),
                "active_power": round(self.electricity.endpoint.getActivePower(), 1),
                "active_energy": self.electricity.endpoint.getActiveEnergy(),
                "power_factor": round(self.electricity.endpoint.getPowerFactor(), 2)
            }
            await self.publish(self.topic_data, self.read(False), True)

    async def start(self):
        await super().start()
        self.bell.task = asyncio.create_task(self.bell_task())
        self.doors.task = asyncio.create_task(self.doors_task())
        self.electricity.task = asyncio.create_task(self.electricity_task())

    def deinit(self):
        super().deinit()
        self.bell.task.cancel()
        self.doors.task.cancel()
        self.electricity.task.cancel()
        # self.player.deinit()
