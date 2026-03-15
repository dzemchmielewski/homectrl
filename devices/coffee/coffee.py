import asyncio
import json

import esp32
import time
from board.board_application import BoardApplication, Facility
from board.board_shared import Exitable
from machine import Pin, deepsleep

# Min odległość między płytką czujnika z maksymalnym poziomem kawy: 30mm

# wymiary styków:
# szerokość: 13mm
# wysokość: 11mm
# grubość: 1mm

# długość 72,, pomiędzy ściankami
# grubość baterii: 19mm


# # Wake up:
# led = Pin(13, Pin.OUT)
#
# wake_pin = Pin(32, Pin.IN, Pin.PULL_DOWN)
# esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ANY_HIGH)
#
# led.off()
#
# deepsleep(20 * 1_000)

import logging

from micropython import const

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

class TaskObject:
    def __init__(self):
        self.atask = None
    def init(self):
        self.atask = asyncio.create_task(self.task())
    async def task(self):
        pass
    def deinit(self):
        self.atask.cancel()

class LedPulses(TaskObject):
    def __init__(self, pin: Pin, pulses: list, initial=False):
        self.pin = pin
        self.pulses = pulses
        self.initial = initial
    async def task(self):
        self.pin.value(self.initial)
        while True:
            for pulse in self.pulses:
                self.pin.toggle()
                await asyncio.sleep_ms(pulse)

class LedShaker(TaskObject):
    def __init__(self, pin: Pin, max_level):
        self.pin = pin
        self.max_level = max_level
        self.level = 0
        self.patterns = [(((i+1)*100*2)//3, 25) for i in range(self.max_level - 2, -1, -1)]

    async def task(self):
        self.pin.value(0)
        while True:
            if self.level > 0:
                for waits in self.patterns[self.level - 1]:
                    self.pin.toggle()
                    await asyncio.sleep_ms(waits)
            else:
                await asyncio.sleep_ms(100)

class Shaker:
    def __init__(self, pin: Pin):
        self.pin = pin
        self.last = time.ticks_us()
        self.pin.irq(handler=self.pulse, trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING))
    def pulse(self, pin):
        self.last = time.ticks_us()
    def isshaking(self):
        return time.ticks_diff(time.ticks_us(), self.last) < 100_000 # 0.1s

class ShakerState(Facility):
    IDLE = const('idle')
    PULSING = const('pulsing')
    GRINDING = const('grinding')
    THRESHOLD = const(3_000) # ms
    PERIOD = const(50) # ms
    MAX_LEVELS = 6

    def __init__(self, shaker: Shaker):
        super().__init__("shakerstate", endpoint=shaker, value=0)
        self.set = time.time_ms()

    @property
    def state(self):
        return ShakerState.IDLE if self.value == 0 \
            else (ShakerState.PULSING if self.value  < ShakerState.MAX_LEVELS
                  else ShakerState.GRINDING)

    async def state_task(self):
        while True:
            if self.endpoint.isshaking():
                if time.time_ms() - self.set > ShakerState.THRESHOLD // (self.value + 1):
                    if self.value < ShakerState.MAX_LEVELS:
                        self.value += 1
            else: # not shaking
                if time.time_ms() - self.set > ShakerState.THRESHOLD // (self.value + 1):
                    if self.value > 0:
                        self.value -= 1

            await asyncio.sleep_ms(ShakerState.PERIOD)


class CoffeeApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'coffee', use_mqtt=False)
        self.shakerstate = ShakerState(Shaker(Pin(32, Pin.IN)))
        self.tasks = [
            LedPulses(Pin(13, Pin.OUT), [25, 475], initial=False),
            LedShaker(Pin(14, Pin.OUT), ShakerState.MAX_LEVELS)
        ]
        self.something = None

    def read(self, to_json = True):
        result = (self.shakerstate.to_dict()
                  | {})
        return json.dumps(result) if to_json else result

    async def some_task(self):
        state = 0
        while not self.exit:
            new_value = self.shakerstate.value
            if new_value != state:
                state = new_value
                self.log.info(f"{'#'*state}{'_' * (ShakerState.MAX_LEVELS - state)} -> {self.shakerstate.state}")
            await asyncio.sleep_ms(100)

    async def start(self):
        await super().start()
        self.shakerstate.task = asyncio.create_task(self.shakerstate.state_task())
        self.something = asyncio.create_task(self.some_task())
        for task in self.tasks:
            task.init()

    def deinit(self):
        super().deinit()
        self.shakerstate.task.cancel()
        self.something.cancel()
        for task in self.tasks:
            task.deinit()

if __name__ == "__main__":
    CoffeeApplication().run()
