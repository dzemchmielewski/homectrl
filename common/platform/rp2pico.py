import machine
import time

class CommonGPIO:

    def __init__(self):
        self.pins = {}

    def setup_out(self, pin):
        self.pins[pin] = machine.Pin(pin, machine.Pin.OUT)

    def setup_in(self, pin):
        self.pins[pin] = machine.Pin(pin, machine.Pin.IN)

    def output(self, pin, signal):
        self.pins[pin].value(signal)

    def input(self, pin):
        return self.pins[pin].value()

    def cleanup(self):
        pass


def log_entry_prefix():
    return "[{}]".format(time.ticks_ms())


def time_ms():
    return time.ticks_ms()
