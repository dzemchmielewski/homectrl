import time
from machine import Pin, ADC
from common.common import Common, time_ms


class DarknessSensor(Common):

    def __init__(self, digital_pin, analog_pin, debug=False):
        super().__init__("darkness", debug=debug)
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
            self.max_floating_time = 30 * 1_000

    @classmethod
    def from_digital_pin(cls, pin, debug=False):
        return cls(pin, None, debug)

    @classmethod
    def from_analog_pin(cls, pin, debug=False):
        return cls(None, pin, debug)

    def read_voltage(self):
        return self.adc.read_uv() / 1_000_000

    def is_darkness(self):
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
        sensor = DarknessSensor("DARKNESS", 9)
        prev = None

        while True:
            value = sensor.is_darkness()
            if value != prev:
                print("CHANGE to {}".format(value))
                prev = value
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass

# exec(open("/modules/darkness_sensor.py").read())
