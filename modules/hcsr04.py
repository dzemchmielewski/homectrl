import asyncio
import time
from machine import Pin

class HCSR04:
    """
    Driver to use the HC-SR04 ultrasonic distance sensor.
    """
    SPEED_CM_US = 0.0343
    TIMEOUT_US = 30000      # us (~5 m max range)
    INTERVAL_MS = 60        # datasheet-safe

    def __init__(self, trigger: int | Pin, echo_pin: int | Pin):
        if isinstance(trigger, int):
            self.trigger = Pin(trigger, Pin.OUT)
        else:
            self.trigger = trigger
        if isinstance(echo_pin, int):
            self.echo = Pin(echo_pin, Pin.IN)
        else:
            self.echo = echo_pin
            # Set trigger to Low
            self.trigger.value(0)
            time.sleep_us(2)

    def _single_measure(self):
        """
        Measure the distance in centimeters.
        """
        # Trigger pulse
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)

        # Wait for echo HIGH
        t0 = time.ticks_us()
        while self.echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), t0) > self.TIMEOUT_US:
                return None
        start = time.ticks_us()

        # Wait for echo LOW
        while self.echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), start) > self.TIMEOUT_US:
                return None
        stop = time.ticks_us()

        return (time.ticks_diff(stop, start) * self.SPEED_CM_US) / 2


    async def measure(self, samples: int = 10, calibration: float = 0) -> float:
        """
        Make 'samples' measurements and return the average.
        """
        values = []

        for _ in range(samples):
            d = self._single_measure()
            if d is not None:
                values.append(d)
            await asyncio.sleep_ms(self.INTERVAL_MS)

        if not values:
            return None

        return (sum(values) / len(values)) + calibration

if __name__ == "__main__":

    async def main_as():
        sensor = HCSR04(trigger=33, echo_pin=25)
        while True:
            dist = await sensor.measure(samples=10, calibration=2.4)
            print(f"Distance: {dist:.2f} cm")
            asyncio.sleep(1)

    def main_sync():
        sensor = HCSR04(trigger=33, echo_pin=25)
        while True:
            dist = asyncio.run(sensor.measure(samples=10, calibration=2.4))
            print(f"Distance: {dist:.2f} cm")
            time.sleep(1)

    asyncio.run(main_as())
    # main_sync()
