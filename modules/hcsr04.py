import asyncio
import time
from machine import Pin

class HCSR04:
    """
    Driver to use the HC-SR04 ultrasonic distance sensor.
    """
    # SPEED_CM_US = 0.0343
    INTERVAL_MS = 60        # datasheet-safe

    def __init__(self, trigger: int | Pin, echo_pin: int | Pin, timeout_us: int | None = None, temperature: float = 20):
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
        self.timeout = timeout_us
        self.sound_speed = 0.03313 + 0.0000606 * temperature

    def _single_measure_timeout(self):
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
            if time.ticks_diff(time.ticks_us(), t0) > self.timeout:
                return None
        start = time.ticks_us()

        # Wait for echo LOW
        while self.echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), start) > self.timeout:
                return None
        stop = time.ticks_us()

        return (time.ticks_diff(stop, start) * self.sound_speed) / 2

    def _single_measure(self):
        """
        Measure the distance in centimeters.
        """
        # Trigger pulse
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)

        # Wait for echo HIGH
        while self.echo.value() == 0:
            pass

        start = time.ticks_us()
        # Wait for echo LOW
        while self.echo.value() == 1:
            pass
        stop = time.ticks_us()

        return (time.ticks_diff(stop, start) * self.sound_speed) / 2

    async def measure(self, samples: int = 10, calibration: float = 0) -> (float, float):
        """
        Make 'samples' measurements and return the average.
        """
        values = []

        for _ in range(samples):
            d = self._single_measure_timeout() if self.timeout else self._single_measure()
            if d is not None:
                values.append(d)
                # print(".", end="")
            else:
                pass
                # print("x", end="")
            await asyncio.sleep_ms(self.INTERVAL_MS)
        if not values:
            # print("NO VALS!!!")
            return None
        else:
            pass
            # print(f" VAL SIZE: {len(values)}")

        # return avg and median, with calibration offset:
        return (sum(values) / len(values)) + calibration, sorted(values)[len(values) // 2] + calibration

if __name__ == "__main__":

    trigg = 5
    echo = 17
    samples = 30
    calibration = 2.4
    exit = False

    async def main_as():
        # 30000us = 30ms, which is enough for ~5m distance (datasheet max is 4m, but let's be safe)
        sensor = HCSR04(trigger=trigg, echo_pin=echo, timeout_us=30000, temperature=22.5)
        while not exit:
            dist, med = await sensor.measure(samples=samples, calibration=calibration)
            print(f"Distance: AVG: {dist:.2f} cm, MED: {med:.2f} cm")
            asyncio.sleep(1)

    def main_sync():
        sensor = HCSR04(trigger=trigg, echo_pin=echo)
        for _ in range(3):
            dist, med = asyncio.run(sensor.measure(samples=samples, calibration=calibration))
            print(f"Distance: AVG: {dist:.2f} cm, MED: {med:.2f} cm")
            time.sleep(1)

    try:
        asyncio.run(main_as())
    except KeyboardInterrupt:
        exit = True
    # main_sync()
