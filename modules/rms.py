import math
import time
from machine import ADC, Pin
from collections import namedtuple

RMSResult = namedtuple("RMSResult", "rms count time")

class RMS:
    def __init__(self, get_single_value_method, max_samples_count: int = 200, max_measure_time_us: int = 1_000_000):
        self.get_single_value_method = get_single_value_method
        self.max_samples_count = max_samples_count
        self.max_measure_time_us = max_measure_time_us
        self.samples = [0.0] * self.max_samples_count
        self.ac_samples = [0.0] * self.max_samples_count

    @staticmethod
    def _mean(array, count):
        mean = 0
        for i in range(count):
            mean += array[i]
        return mean / count

    @staticmethod
    def _rms(array, count):
        sum2 = 0
        for i in range(count):
            sum2 += array[i]**2
        return math.sqrt(sum2 / count)

    def get(self):
        count = 0
        start = time.ticks_us()
        while time.ticks_diff(time.ticks_us(), start) < self.max_measure_time_us and count < len(self.samples):
            self.samples[count] = self.get_single_value_method()
            count += 1
        time_taken = time.ticks_diff(time.ticks_us(), start)

        mean = self._mean(self.samples, count)
        for i in range(count):
            self.ac_samples[i] = self.samples[i] - mean

        return RMSResult(self._rms(self.ac_samples, count), count, time_taken)

if __name__ == "__main__":
    pin = 2
    adc = ADC(Pin(pin, mode=Pin.IN))
    adc.atten(ADC.ATTN_11DB)
    rms = RMS(lambda: adc.read_uv() / 1_000_000, max_samples_count=1_500, max_measure_time_us=200_000)

    try:
        while True:
            result = rms.get()
            print(f"AC RMS: {result.rms:.4f} RESULT: {result}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("EXIT")
