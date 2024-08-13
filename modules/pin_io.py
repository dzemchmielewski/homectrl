from common.common import Common


class PinIO(Common):

    IS_INPUT = 0
    IS_OUTPUT = 1

    def __init__(self, name, pin, debug=False):
        super().__init__(name, debug)
        self.pin = pin
        self.state = None

    def get_signal(self):
        if not self.state or self.state == self.IS_OUTPUT:
            self.gpio.setup_in(self.pin)
            self.state = self.IS_INPUT
        return self.gpio.input(self.pin)

    def set_signal(self, signal):
        if not self.state or self.state == self.IS_INPUT:
            self.gpio.setup_out(self.pin)
            self.state = self.IS_OUTPUT
        self.gpio.output(self.pin, signal)

