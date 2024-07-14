from datetime import datetime
import time
import serial

def log_entry_prefix():
    return "{:%Y-%m-%d %H:%M:%S.%f}".format(datetime.now())


def time_ms():
    return int(round(time.time() * 1000))


class CommonSerial(serial.Serial):

    def __init__(self,
                 port=None,
                 baudrate=9600,
                 bytesize=serial.EIGHTBITS,
                 parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE,
                 timeout=None):
        super().__init__(port, baudrate, bytesize, parity, stopbits, timeout)
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout

    def reinit(self):
        self.reset_input_buffer()
        # return CommonSerial(self.port, self.baudrate, self.bytesize, self.parity, self.stopbits, self.timeout)

