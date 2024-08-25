import time

from common.common import Common, time_ms


class DarknessSensor(Common):

    def __init__(self, name, pin, debug=False):
        super().__init__(name, debug=debug)
        self.pin = pin
        self.gpio.setup_in(self.pin)

        # When LED is on it is light enough - pin signal is zero
        self.current_value = self.gpio.input(self.pin)
        self.is_floating = False
        self.floating_time = None
        self.max_floating_time = 30 * 1_000

    def is_darkness(self):
        value = self.gpio.input(self.pin)

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
