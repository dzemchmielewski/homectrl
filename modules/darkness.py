import time
from collections import deque

from machine import Pin, ADC
from common.common import Common, time_ms


class DarknessSensor(Common):

    def __init__(self, digital_pin, analog_pin):
        super().__init__("darkness")
        self.digital_pin = digital_pin
        if digital_pin:
            self.gpio.setup_in(self.digital_pin)

        if analog_pin:
            self.adc = ADC(Pin(analog_pin, mode=Pin.IN))
            self.adc.atten(ADC.ATTN_11DB)

        # When LED is on it is light enough - pin signal is zero
        if self.digital_pin:
            self.current_value = self.gpio.input(self.digital_pin)
            self.is_floating = False
            self.floating_time = None
            self.max_floating_time = None
        else:
            self.queue = None
            self.voltage_threshold = None

    @classmethod
    def from_digital_pin(cls, pin: int, floating_time_sec: int = 30):
        instance = cls(pin, None)
        instance.max_floating_time = floating_time_sec * 1_000
        return instance

    @classmethod
    def from_analog_pin(cls, pin: int, queue_size: int = 10, voltage_threshold: float = 2.31):
        instance = cls(None, pin)
        instance.queue = deque((), queue_size)
        instance.voltage_threshold = voltage_threshold
        return instance

    def read_analog(self):
        voltage = self.adc.read_uv() / 1_000_000
        self.queue.append(voltage)
        lst = list(self.queue)
        mean_voltage = sum(lst)/len(lst)
        return mean_voltage >= self.voltage_threshold, mean_voltage, voltage

    def read_digital(self):
        value = self.gpio.input(self.digital_pin)

        if value != self.current_value:

            if not self.is_floating:
                self.is_floating = True
                self.floating_time = time_ms()

            else:
                if time_ms() - self.floating_time > self.max_floating_time:
                    self.is_floating = False
                    self.floating_time = None
                    self.current_value = value
                    self.log("ON -> OFF" if not value else "OFF -> ON")

        else:
            if self.is_floating:
                self.is_floating = False
                self.floating_time = None

        return self.current_value


if __name__ == '__main__':
    try:
        sensor = DarknessSensor.from_analog_pin(4, 5, 2.31)
        while True:
            print("{}: mean:{}, current: {}".format(*sensor.read_analog()))
            time.sleep(1)
    except KeyboardInterrupt:
        pass

# exec(open("/modules/darkness.py").read())
