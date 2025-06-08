import asyncio
import logging
import time

from machine import Pin

# shift register
class SR74HC595:

    def __init__(self, length, data_pin: int, clock_pin, latch_pin, delay_ms: int = None):
        self.length = length
        self.delay_ms = delay_ms
        self.latch_pin = Pin(latch_pin, Pin.OUT)
        self.clock_pin = Pin(clock_pin, Pin.OUT)
        self.data_pin = Pin(data_pin, Pin.OUT)
        for pin in [self.latch_pin, self.clock_pin, self.data_pin]:
            pin.value(0)

    async def _pulse_as(self, pin: Pin):
        for signal in [1, 0]:
            pin.value(signal)
            if self.delay_ms:
                await asyncio.sleep_ms(self.delay_ms)

    async def _set_as(self, value):
        for _ in range(self.length):
            logging.debug("data pin: {}".format(value & 1))
            self.data_pin.value(value & 1)
            await self._pulse_as(self.clock_pin)
            value = value >> 1
        await self._pulse_as(self.latch_pin)

    def _pulse_sync(self, pin: Pin):
        for signal in [1, 0]:
            pin.value(signal)
            if self.delay_ms:
                time.sleep_ms(self.delay_ms)

    def _set_sync(self, value):
        for _ in range(self.length):
            logging.debug("data pin: {}".format(value & 1))
            self.data_pin.value(value & 1)
            self._pulse_sync(self.clock_pin)
            value = value >> 1
        self._pulse_sync(self.latch_pin)


class SR74HC595_AS(SR74HC595):
    def __init__(self, length, data_pin: int, clock_pin, latch_pin, delay_ms: int = None):
        super().__init__(length, data_pin, clock_pin, latch_pin, delay_ms)
    async def set(self, value):
        await self._set_as(value)


class SR74HC595_Sync(SR74HC595):
    def __init__(self, length, data_pin: int, clock_pin, latch_pin, delay_ms: int = None):
        super().__init__(length, data_pin, clock_pin, latch_pin, delay_ms)
    def set(self, value):
        self._set_sync(value)
