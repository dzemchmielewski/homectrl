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
    return "{}".format(time.ticks_ms())


def time_ms():
    return time.ticks_ms()


class CommonSerial(machine.UART):

    def __init__(self, id: int, baudrate: int = 9600, bits: int = 8, parity: int | None = None, stop: int = 1, tx: int | None = None, rx: int | None = None, timeout: int | None = None):
        super().__init__(id)
        self.init(baudrate=baudrate, bits=bits, parity=parity, stop=stop, tx=machine.Pin(tx), rx=machine.Pin(rx), timeout=timeout)
        self.id = id
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.tx = tx
        self.rx = rx
        self.timeout = timeout

    def reinit(self):
        self.init(baudrate=self.baudrate, bits=self.bits, parity=self.parity,stop=self.stop, tx=self.tx, rx=self.rx, timeout=self.timeout)
