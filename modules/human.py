from common.common import Common, time_ms


class HumanSensor(Common):

    def __init__(self, name, pin, debug=False):
        super().__init__(name, debug=debug)
        self.pin = pin
        self.gpio.setup_in(self.pin)

        self.current_value = self.gpio.input(self.pin)

    def is_detected(self):
        return self.gpio.input(self.pin)
