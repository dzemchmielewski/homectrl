from common.common import Common


class PinIO(Common):

    IS_INPUT = 0
    IS_OUTPUT = 1

    def __init__(self,  pin: int, set_initial=None):
        super().__init__("PinIO")
        self.pin = pin
        self.state = None
        if set_initial:
            self.set(set_initial)
        else:
            self.last_set = 0

    def get(self):
        if not self.state or self.state == self.IS_OUTPUT:
            self.gpio.setup_in(self.pin)
            self.state = self.IS_INPUT
        return self.gpio.input(self.pin)

    def set(self, signal: int | bool):
        if isinstance(signal, bool):
            signal = int(signal)
        if not self.state or self.state == self.IS_INPUT:
            self.gpio.setup_out(self.pin)
            self.state = self.IS_OUTPUT
        self.last_set = signal
        self.gpio.output(self.pin, signal)

    def on(self):
        self.set(True)

    def off(self):
        self.set(False)

    def toggle(self):
        self.set(not self.last_set)
