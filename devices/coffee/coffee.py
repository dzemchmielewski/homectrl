import logging

LOG_TO_FILE = False
if LOG_TO_FILE:
    logfile = open("log.txt", "a")
    logging.basicConfig(
        level=logging.WARNING,
        stream=logfile,
    )
else:
    logging.basicConfig(
        level=logging.WARNING,
    )

for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
logger = logging.getLogger(__name__)

import time
import asyncio
import json
import esp32
import framebuf

from micropython import const
from machine import Pin, deepsleep, SPI, SoftI2C

from board.board_application import BoardApplication, Facility, TaskObject
from epd2in9v4 import EPD2in9V4
from view import CoffeeView
from max17043 import MAX17043
from shaker import Shaker, GRINDING, IDLE
from hcsr04 import HCSR04

IDLE_SLEEP_TIMEOUT = const(90) # sec

LID_OPENED = const(0x1)
LID_CLOSED = const(0x0)

MSG_DEFAULT = const("bedziem mielu?")
MSG_LID_OPENED = const("włajaż włajaż")
MSG_GRINDING = "mielu mielu"
MSG_GRINDING_COMPLETE = "zmełłem"
MSG_COFFEE_PANIC = "panika !!!"

LEVEL_MEASURE_SAMPLES = 11 # odd number to easy find the median
#LEVEL_MEASURE_CALIBRATION = 2.4
LEVEL_MEASURE_CALIBRATION = -2.4
LEVEL_MEASURE_MAX = 12.6


class LedPulses(TaskObject):
    def __init__(self, pin: Pin, pulses: list, initial=False):
        super().__init__()
        self.pin = pin
        self.pulses = pulses
        self.initial = initial

    async def task(self):
        self.pin.value(self.initial)
        while True:
            for pulse in self.pulses:
                self.pin.toggle()
                await asyncio.sleep_ms(pulse)

class Button(TaskObject, Facility):
    def __init__(self, name: str, pin: Pin, on_click: callable, on_long_click: callable):
        TaskObject.__init__(self)
        Facility.__init__(self, name, pin, None)
        del self.task  # Facility.__init__ sets self.task=None, shadowing the task() method
        self.on_click = on_click
        self.on_long_click = on_long_click

    async def task(self):
        self.value = self.endpoint.value()
        while True:
            new_value = self.endpoint.value()
            if  new_value != self.value:
                delta = time.time_ms() - self.set
                self.value = new_value
                if new_value == 0:
                    if delta >= 3_000:
                        await self.on_long_click()
                    else:
                        await self.on_click()
            elif new_value == 1:
                if time.time_ms() - self.set >= 3_000:
                    await self.on_long_click()

            await asyncio.sleep_ms(100)

class CoffeeApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'coffee', use_mqtt=False)
        # LED orange 26 - shaker indicator
        # LED yellow 33 - one second ping stating device alive
        # LED blue 25 - display indicator
        # Red button 35
        # shaker input 32
        # HCSR: 17, 5
        # lid magnetic sensor 18
        # Battery - pins 12, 14

        self.shaker = Shaker(Pin(32, Pin.IN), Pin(26, Pin.OUT), self.shaker_event)
        self.redbtn = Button("redbtn", Pin(35, Pin.IN, Pin.PULL_DOWN), self.click_event, self.long_click_event)
        self.tasks = [
            LedPulses(Pin(33, Pin.OUT), [5, 995], initial=False),
            self.shaker,
            self.redbtn,
        ]

        # Display - pins 4, 16, 0, 2, 15, 13
        self.sck, self.mosi = Pin(4), Pin(16)
        self.epd = EPD2in9V4(
            128, 296,
               None, #SPI
                         Pin(0, Pin.OUT), #CS
                         Pin(2, Pin.OUT), #DC
                         Pin(15, Pin.OUT), #RST
                         Pin(13, Pin.IN)) #BUSY
        self.view = CoffeeView(296, 128, framebuf.MONO_HLSB)
        self.display = Facility("display", Pin(25, Pin.OUT), False)
        self.lid = Facility("lid", Pin(18, Pin.IN), None)
        self.level = HCSR04(trigger=Pin(5, Pin.OUT), echo_pin=Pin(17, Pin.IN))
        self.battery = Facility("battery", MAX17043(SoftI2C(scl=Pin(12), sda=Pin(14))),
                                to_dict=lambda x : {'battery': {'value': x.value[0], 'voltage': x.value[1]}} if x.value is not None else {})
        self.gosleep = Facility("gosleep", None, False)

        self.data: dict = {
            'battery': {
                'value': None,
                'alert': False,
            },
            'coffee': {
                'value': None,
                'alert': False,
            },
            'message': {
                'value': None,
                'alert': False,
            },
        }

    def read(self, to_json = True):
        result = (self.shaker.to_dict()
                  | {})
        return json.dumps(result) if to_json else result

    def dataset(self, node = None, value = None, alert = False):
        if node:
            self.data[node]['value'], self.data[node]['alert'] = value, alert
        else:
            self.dataset('coffee')
            self.dataset('message')

    def shaker_event(self, state):
        logger.debug(f"SHAKER state: {state}")
        if self.lid.value == LID_CLOSED:
            if state == GRINDING:
                self.dataset('message', MSG_GRINDING, False)
            elif state == IDLE:
                self.dataset('message', MSG_GRINDING_COMPLETE, False)
                self.dataset('coffee')
            else:
                return
            self.display.value = True
        else:
            # no action when lid is opened
            pass

    async def click_event(self):
        logger.debug("RED BUTTON clicked")
        await self.read_level()
        self.display.value = True

    async def long_click_event(self):
        logger.debug("RED BUTTON long clicked")
        import machine
        machine.reset()

    def read_battery(self):
        self.battery.value = (min(100, round(self.battery.endpoint.soc)), self.battery.endpoint.voltage, self.battery.endpoint.undervoltage)
        self.data['battery']['value'] = (12 * self.battery.value[0] + 99) // 100
        self.data['battery']['alert'] = self.battery.endpoint.undervoltage

    async def read_level(self):
        dist, med = await self.level.measure(samples=LEVEL_MEASURE_SAMPLES, calibration=LEVEL_MEASURE_CALIBRATION)
        # self.dataset("coffee", round(med, 1))
        # level in cm to %:
        perc = min(100, 100 - round((med * 100) / LEVEL_MEASURE_MAX))
        perc = 0 if perc <= 0 else perc
        if 5 < perc <= 15:
            self.dataset("coffee", perc, True)
        elif perc <= 5:
            self.dataset("coffee", perc, True)
            self.dataset("message", MSG_COFFEE_PANIC, True)
        else:
            self.dataset("coffee", perc, False)


    @staticmethod
    def required(*args):
        return all(a is not None for a in args)

    async def wait_until_ready(self):
        if self.data['battery']['value'] is None:
            self.read_battery()
        if self.data['coffee']['value'] is None:
            await self.read_level()
        logger.debug(f"WAIT... battery: {self.data['battery']['value']}, coffee: {self.data['coffee']['value']}, message: {self.data['message']['value']}")
        while not self.required(
                self.data['battery']['value'],
                self.data['coffee']['value']):
            await asyncio.sleep_ms(100)

    async def display_task(self):
        while not self.exit:
            if self.display.value:
                logger.debug("DISPLAY TASK init")
                self.display.endpoint.on()
                await self.wait_until_ready()
                logger.debug("DISPLAY TASK start")

                try:
                    self.display.value = False
                    self.epd.spi = SPI(1, baudrate=4_000_000, sck=self.sck, mosi=self.mosi)
                    self.view.render(self.data)
                    await self.epd.init()
                    # await self.epd.clear()
                    await self.epd.display(self.view.black_out.buffer, self.view.red_out.buffer)
                    await self.epd.sleep()
                finally:
                    self.epd.deinit()
                    self.display.endpoint.off()

                # self.display.endpoint.on()
                # self.display.value = False
                # await asyncio.sleep(2)
                # self.display.endpoint.off()

                logger.debug(f"DISPLAY TASK end (next value: {self.display.value})")
            await asyncio.sleep_ms(100)

    async def lid_task(self):
        self.lid.set = time.ticks_ms()
        while not self.exit:
            current = self.lid.endpoint.value()
            if self.lid.value != current:
                logger.debug(f"LID state: {current}")
                self.lid.value = current
                if current == LID_OPENED:
                    self.dataset('message', MSG_LID_OPENED, True)
                else:
                    # wait a little, to make sure the level sensor is already on place.
                    await asyncio.sleep_ms(200)
                    self.dataset('message', MSG_DEFAULT)
                    self.dataset('coffee')
                self.display.value = True
            await asyncio.sleep_ms(100)

    async def gosleep_task(self):
        while not self.exit:
            last_action = max(self.lid.set, self.shaker.last_signal)
            # logger.warning(f"SLEEP? lid: {self.lid.set}, shaker: {self.shaker.last_signal}, max: {last_action}")
            if time.time_ms() - last_action > IDLE_SLEEP_TIMEOUT * 1_000:
                self.dataset('message')
                self.gosleep.value = True
                self.display.value = True
                # wait for display task:
                await asyncio.sleep_ms(100)
                # wait for display refresh:
                while self.display.endpoint.value() == 1:
                    await asyncio.sleep_ms(100)
                # finally go to sleep:
                esp32.wake_on_ext0(pin=self.shaker.endpoint, level=esp32.WAKEUP_ANY_HIGH)
                deepsleep()
            await asyncio.sleep(1)

    async def logfile_task(self):
        while not self.exit:
            logfile.flush()
            await asyncio.sleep_ms(300)

    async def start(self):
        await super().start()
        self.display.task = asyncio.create_task(self.display_task())
        self.lid.task = asyncio.create_task(self.lid_task())
        self.gosleep.task = asyncio.create_task(self.gosleep_task())
        if LOG_TO_FILE:
            self.logfile_task = asyncio.create_task(self.logfile_task())
        for task in self.tasks:
            task.init()

    def deinit(self):
        super().deinit()
        self.display.task.cancel()
        self.lid.task.cancel()
        self.gosleep.task.cancel()
        if LOG_TO_FILE:
            self.logfile_task.cancel()
        for task in self.tasks:
            task.deinit()

if __name__ == "__main__":
    CoffeeApplication().run()
