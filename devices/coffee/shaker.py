import asyncio
import time

from array import array

from machine import Pin
from micropython import const

from board.board_application import TaskObject, Facility

IDLE     = const('idle')
GRINDING = const('grinding')

_SHAKER_BUF      = const(64)
_WINDOW_MS       = const(500)
_GRIND_THRESHOLD = const(8)
_IDLE_TIMEOUT_MS  = const(2000)
_GRIND_CONFIRM_MS = const(600)
_PERIOD_MS        = const(10)

_LED_PATTERNS = {
    IDLE:     None,
    GRINDING: (50, 50),
}


class LedShaker(TaskObject):
    def __init__(self, pin: Pin):
        super().__init__()
        self.pin = pin
        self.state = IDLE

    async def task(self):
        self.pin.value(0)
        while True:
            pattern = _LED_PATTERNS[self.state]
            if pattern is None:
                self.pin.value(0)
                await asyncio.sleep_ms(20)
            else:
                for ms in pattern:
                    self.pin.toggle()
                    await asyncio.sleep_ms(ms)

    def deinit(self):
        super().deinit()
        self.pin.value(0)


class Shaker(TaskObject, Facility):
    def __init__(self, pin_shaker: Pin, pin_led: Pin, on_change: callable):
        TaskObject.__init__(self)
        Facility.__init__(self, "shaker", endpoint=pin_shaker, value=IDLE)
        self.on_change = on_change
        sentinel = time.ticks_add(time.ticks_ms(), -(_WINDOW_MS + 1))
        self._buf = array('l', [sentinel] * _SHAKER_BUF)
        self._head = 0
        self.led = LedShaker(pin_led)
        self.last_signal = time.time_ms()
        self._grind_since = None

    def init(self):
        del self.task  # Facility.__init__ sets self.task=None, shadowing the task() method
        super().init()
        self.led.init()

    async def task(self):
        last_pin_value = self.endpoint.value()
        while True:
            await asyncio.sleep_ms(2)
            current = self.endpoint.value()

            if current != last_pin_value:
                last_pin_value = current
                self._buf[self._head % _SHAKER_BUF] = time.ticks_ms()
                self._head += 1
                self.last_signal = time.time_ms()

            if self.idle_ms() > _IDLE_TIMEOUT_MS:
                new_state = IDLE
                self._grind_since = None
            elif self.rate(_WINDOW_MS) >= _GRIND_THRESHOLD:
                if self._grind_since is None:
                    self._grind_since = time.ticks_ms()
                if time.ticks_diff(time.ticks_ms(), self._grind_since) >= _GRIND_CONFIRM_MS:
                    new_state = GRINDING
                else:
                    new_state = self.value
            else:
                self._grind_since = None
                new_state = self.value
            if self.value != new_state:
                self.value = new_state
                self.led.state = new_state
                self.on_change(new_state)

    def rate(self, window_ms: int) -> int:
        now = time.ticks_ms()
        cutoff = time.ticks_add(now, -window_ms)
        return sum(1 for t in self._buf if time.ticks_diff(t, cutoff) >= 0)

    def idle_ms(self) -> int:
        if self._head == 0:
            return 60 * 60 * 1000
        last = self._buf[(self._head - 1) % _SHAKER_BUF]
        return time.ticks_diff(time.ticks_ms(), last)

    def deinit(self):
        super().deinit()
        self.led.deinit()
