import time
import asyncio

from machine import PWM

class PWMFade:
    """
    Class to control PWM fading with gamma correction.

    Attributes:
        STEP_DELAY (int): Delay between steps in milliseconds.
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
        current = self.to_percent(self.pwm.duty())
        target = min(max(to_percent, 0), 100)
        step = (self.STEP_DELAY / 1_000) * speed # percents per step
        direction = 1 if target > current else -1
        while (direction == 1 and current < target) or (direction == -1 and current > target):
            start = time.ticks_ms()
            self.pwm.duty(self.to_duty(current))
            current += direction * step
            while time.ticks_ms() - start < self.STEP_DELAY:
                await asyncio.sleep_ms(0)

        if target == 0.0:
            self.pwm.duty(0)
        elif target == 100.0:
            self.pwm.duty(self.max_duty)

    def deinit(self):
        if self.task is not None:
            self.task.cancel()
        self.pwm.deinit()
