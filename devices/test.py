import time
import asyncio
import json
import logging

import machine
from machine import Pin, Timer

from board.board_application import BoardApplication
from board.boot import Boot
from configuration import Configuration
from ping import ping
from board.board_shared import Utils as util
import upysh

from toolbox.pinio import PinIO

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class TestApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'test', use_mqtt=True)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        self.read_ping = None
        self.ping = (0, 0)

        self.led_pin = PinIO(12, False)

        self.button_pin = Pin(13, Pin.IN, Pin.PULL_DOWN)
        self.button_pin.irq(trigger=Pin.IRQ_RISING, handler=self.button_handler)

        # self.timer = Timer(0)
        # self.timer.init(period=10*1_000, mode=Timer.PERIODIC, callback=self.ping_task)


    def button_handler(self, button_pin):
        logging.info("TestApplication.button_handler: %s", self.button_pin)
        upysh.cp('secrets.json_ORIG', 'secrets.json')
        upysh.cp('configuration.py_ORIG', 'configuration.py')
        logging.info("TestApplication.button_handler completed.")
        machine.reset()

    def read(self, to_json = True):
        result = {
            "read_ping": self.read_ping,
            "ping": self.ping
        }
        logging.info("TestApplication.read: %s", result)
        return json.dumps(result) if to_json else result

    async def ping_task(self):
        while not self.exit:
            self.read_ping = util.time_str()
            ifconfig = Boot.get_instance().wifi.ifconfig()
            logging.info("TestApplication.ping_task: ifconfig:  %s", ifconfig)
            logging.info("TestApplication.ping_task: wifi isconnected:  %s", Boot.get_instance().wifi.isconnected())
            if ifconfig[2] != '0.0.0.0':
                self.ping = ping(ifconfig[2], count=5, quiet=True)
                logging.info("TestApplication.ping_task: %s", self.ping)
                await self.publish(self.topic_data, f"[{self.read_ping}] PING values: {self.ping}", True)
            else:
                logging.info("TestApplication.ping_task: no ip")
                await self.publish(self.topic_data, f"[{self.read_ping}] PING - no IP", True)
            await asyncio.sleep(10)

    async def led_task(self):
        while not self.exit:
            self.led_pin.toggle()
            await asyncio.sleep_ms(500)
        self.led_pin.off()

    async def start(self):
        logging.info("TestApplication.start")
        await super().start()
        logging.info("TestApplication.start after super().start()")
        self._led_task = asyncio.create_task(self.led_task())
        logging.info("TestApplication.start after led_task()")
        self._ping_task = asyncio.create_task(self.ping_task())
        logging.info("TestApplication.start completed")

    def deinit(self):
        super().deinit()
        # self.timer.deinit()
        self._led_task.cancel()
        self._ping_task.cancel()

from upysh import *
cp('secrets.json_TEST', 'secrets.json')
cp('configuration.py_TEST', 'configuration.py')
