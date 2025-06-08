import time
import ustruct
from machine import SPI, Pin


class MAX31855:
    """
    Driver for the MAX31855 thermocouple amplifier.
    MicroPython example::
        import max31855
        from machine import SPI, Pin
        spi = SPI(1, baudrate=1000000)
        cs = Pin(15, Pin.OUT)
        s = max31855.MAX31855(spi, cs)
        print(s.read())
    """
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.data = bytearray(4)

    def read(self, internal=False, raw=False):
        """
        Read the measured temperature.
        If ``internal`` is ``True``, return a tuple with the measured
        temperature first and the internal reference temperature second.
        If ``raw`` is ``True``, return the values as 14- and 12- bit integers,
        otherwise convert them to Celsuius degrees and return as floating point
        numbers.
        """

        self.cs.off()
        try:
            self.spi.readinto(self.data)
        finally:
            self.cs.on()
        # The data has this format:
        # 00 --> OC fault
        # 01 --> SCG fault
        # 02 --> SCV fault
        # 03 --> reserved
        # 04 -. --> LSB
        # 05  |
        # 06  |
        # 07  |
        #      > reference
        # 08  |
        # 09  |
        # 10  |
        # 11  |
        # 12  |
        # 13  |
        # 14  | --> MSB
        # 15 -' --> sign
        #
        # 16 --> fault
        # 17 --> reserved
        # 18 -.  --> LSB
        # 19   |
        # 20   |
        # 21   |
        # 22   |
        # 23   |
        #       > temp
        # 24   |
        # 25   |
        # 26   |
        # 27   |
        # 28   |
        # 29   |
        # 30   | --> MSB
        # 31  -' --> sign
        if self.data[3] & 0x01:
            raise RuntimeError("thermocouple not connected")
        if self.data[3] & 0x02:
            raise RuntimeError("short circuit to ground")
        if self.data[3] & 0x04:
            raise RuntimeError("short circuit to power")
        if self.data[1] & 0x01:
            raise RuntimeError("faulty reading")
        temp, refer = ustruct.unpack('>hh', self.data)
        refer >>= 4
        temp >>= 2
        if raw:
            if internal:
                return temp, refer
            return temp
        if internal:
            return temp / 4, refer * 0.0625
        return temp / 4

class MAX31855_PlanB:

    def __init__(self, sck, miso, cs):
        self.cs = cs
        self.miso = miso
        self.sck = sck
        self.cs.on()
        self.sck.off()
        self.bits = []

    def read(self):
        self.cs.off()
        try:
            self.bits = [self.__read_bit() for _ in range(32)]
        finally:
            self.cs.on()

    def __read_bit(self):
        self.sck.on()
        time.sleep_ms(1)
        bit = self.miso.value()
        self.sck.off()
        time.sleep_ms(1)
        return bit


    #if __name__ == "__main__":

from machine import SPI, Pin
from max31855 import MAX31855
from max31855 import MAX31855_PlanB
import ustruct, time

sck, miso, cs =Pin(13, Pin.OUT), Pin(11, Pin.IN), Pin(12, Pin.OUT)
therm = MAX31855_PlanB(sck, miso, cs)

# sck, miso, cs =Pin(13), Pin(11), Pin(12, Pin.OUT)
sck, miso, cs =Pin(0), Pin(2), Pin(1, Pin.OUT)
therm = MAX31855(SPI(1, sck=sck, miso=miso, baudrate=5_000_000), cs)

therm.read()

"".join(str(i) for i in therm.bits)


def r():
    while True:
        print(f" --> {therm.read(internal=True)}")
        time.sleep(1)

def rr():
    while True:
        print(f" --> {therm.read_raw()/4}")
        time.sleep(1)

