from micropython import const
from machine import Pin

class PinIO:

    IN = const('in')
    OUT = const('out')

    def __init__(self,  pin: int, set_initial: int | bool = None, pull: int = -1):
        self.pin_number = pin
        self. pull = pull
        self.pin = None
        self.state = None
        self.last_value = None
        if set_initial is not None:
            self.set(set_initial)

    def get(self):
        if not self.state or self.state != PinIO.IN:
            self.pin = Pin(self.pin_number, Pin.IN, self.pull)
            self.state = PinIO.IN
        self.last_value = self.pin.value()
        return self.last_value

    def set(self, signal: int | bool):
        if not self.state or self.state != PinIO.OUT:
            self.pin = Pin(self.pin_number, Pin.OUT, self.pull)
            self.state = PinIO.OUT
        self.last_value = int(signal) if isinstance(signal, bool) else signal
        self.pin.value(self.last_value)
        return self.last_value

    def on(self):
        return self.set(True)

    def off(self):
        return self.set(False)

    def toggle(self):
        return self.set((self.last_value + 1) % 2)
