import time
import asyncio

from machine import PWM

class PWMFade:
    """
    Class to control PWM fading with gamma correction.

    Attributes:
        pwm (PWM): PWM instance to control.
        gamma (float): Gamma correction factor.
        dmin (float): Minimum duty cycle as a fraction.
        max_duty (int): Maximum duty cycle value.
    """

    STEP_DELAY = 20  # ms

    def __init__(self, pwm: PWM, gamma: float = 2.0, dmin: float = 0.001, max_duty: int = 1023):
        """
        Initialize PWMFade.

        Args:
            pwm (PWM): PWM instance to control.
            gamma (float, optional): Gamma correction factor. Defaults to 2.0.
            dmin (float, optional): Minimum duty cycle as a fraction. Defaults to 0.0.
            max_duty (int, optional): Maximum duty cycle value. Defaults to 1023.
        """
        self.pwm = pwm
        self.gamma = gamma
        self.dmin = dmin
        self.max_duty = max_duty
        self.value = 0.0 # target brightness in percent (set when a fade starts)
        self.task = None

    def to_duty(self, percent: float) -> int:
        """
        Convert a percentage value to a PWM duty cycle, applying gamma correction.

        Args:
            percent (float): Percentage (0-100).

        Returns:
            int: Corresponding duty cycle value.
        """
        b = min(max(percent, 0), 100) / 100
        return round(self.max_duty * ((b ** self.gamma) * (1 - self.dmin) + self.dmin))

    def to_percent(self, duty: int) -> float:
        """
        Convert a PWM duty cycle value to a percentage, applying gamma correction.

        Args:
            duty (int): Duty cycle value.

        Returns:
            float: Corresponding percentage (0-100).
        """
        b = ((min(max(duty, 0), self.max_duty) / self.max_duty) - self.dmin) / (1 - self.dmin)
        b = max(b, 0.0)  # avoid negative at very low duty
        return 100 * (b ** (1 / self.gamma))

    @property
    def current(self) -> float:
        """Actual brightness in percent, derived from the live PWM duty."""
        return self.to_percent(self.pwm.duty())

    def start_fade(self, to_percent: float, speed: float) -> None:
        """
        Non-async variant of fade(): cancel any running fade and start a new one
        immediately, without yielding to the scheduler. Lets PWMArray start all
        channels in the same tick.
        """
        if self.task is not None:
            self.task.cancel()
        self.task = asyncio.create_task(self._fade(to_percent, speed))

    async def fade(self, to_percent: float, speed: float) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.sleep_ms(0)
        self.task = asyncio.create_task(self._fade(to_percent, speed))

    async def _fade(self, to_percent: float, speed: float) -> None:
        """
        Fade the PWM output to a target percentage at a specified speed.

        Args:
            to_percent (float): Target percentage (0-100).
            speed (float): Speed in percent per second.
        """
        self.value = to_percent
        current = self.current
        target = min(max(to_percent, 0), 100)
        direction = 1 if target > current else -1
        last = time.ticks_ms()
        while (direction == 1 and current < target) or (direction == -1 and current > target):
            self.pwm.duty(self.to_duty(current))
            # busy-wait (cooperatively) until at least STEP_DELAY ms have passed;
            # ticks_diff() is safe across ticks_ms() wrap-around
            while True:
                await asyncio.sleep_ms(0)
                now = time.ticks_ms()
                dt = time.ticks_diff(now, last)
                if dt >= self.STEP_DELAY:
                    break
            last = now
            # scale the step by the real elapsed time so the fade duration
            # does not drift when the event loop is busy
            current += direction * speed * dt / 1_000

        if target == 0.0:
            self.pwm.duty(0)
        else:
            self.pwm.duty(self.to_duty(target))  # to_duty(100) already gives max_duty

    def deinit(self):
        if self.task is not None:
            self.task.cancel()
        self.pwm.deinit()


class PWMArray:

    INSTANT_SPEED = 1_000_000  # percent/s, used when seconds <= 0 (jump to target)

    def __init__(self, pwms: list[PWMFade], brightness: list[int]):
        self.pwms = pwms
        self.brightness = brightness
        self.value = False
        for fade in self.pwms:
            fade.pwm.duty(0)

    def _speed(self, delta: float, seconds: float | int) -> float:
        """Speed (percent/s) needed to cover delta in the given time."""
        if seconds <= 0:
            return self.INSTANT_SPEED
        return abs(delta) / seconds

    async def chng_brightness(self, new_brightness: list[int], seconds: float | int):
        if self.brightness != new_brightness:
            # new_brightness = list(new_brightness)  # copy, don't keep the caller's list
            if self.value:
                for i in range(len(self.brightness)):
                    if self.brightness[i] != new_brightness[i]:
                        speed = self._speed(new_brightness[i] - self.pwms[i].current, seconds)
                        self.pwms[i].start_fade(new_brightness[i], speed)
            self.brightness = new_brightness

    async def fadein(self, seconds: float | int):
        if not self.value:
            self.value = True
            for i in range(len(self.pwms)):
                speed = self._speed(self.brightness[i] - self.pwms[i].current, seconds)
                self.pwms[i].start_fade(self.brightness[i], speed)

    async def fadeout(self, seconds: float | int):
        if self.value:
            self.value = False
            for i in range(len(self.pwms)):
                self.pwms[i].start_fade(0, self._speed(self.pwms[i].current, seconds))

    def deinit(self):
        for pwm in self.pwms:
            pwm.deinit()



