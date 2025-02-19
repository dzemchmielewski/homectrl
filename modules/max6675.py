from machine import Pin
from collections import deque
import utime

class MAX6675:

    def __init__(self, so_pin=14, cs_pin=13, sck_pin=12):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.so = Pin(so_pin, Pin.IN)
        self.sck = Pin(sck_pin, Pin.OUT)

        self.cs.on()
        self.so.off()
        self.sck.off()

        self.queue = deque((), 12)

    def read(self):
        data = self.__read_data()
        volts = sum([b * (1 << i) for i, b in enumerate(reversed(data))])
        self.queue.append(volts * 0.25)
        lst = list(self.queue)
        mean_temp = sum(lst)/len(lst)
        return round(mean_temp)

    def __read_data(self):
        # CS down, read bytes then cs up
        self.cs.off()
        utime.sleep_us(10)
        data = self.__read_word() # (self.__read_byte() << 8) | self.__read_byte()
        self.cs.on()

        # print(data)
        # print(data[1:-3])

        if data[-3] == 1:
            raise NoThermocoupleAttached()

        return data[1:-3]

    def __read_word(self):
        return [self.__read_bit() for _ in range(16)]


    def __read_bit(self):
        self.sck.off()
        utime.sleep_us(10)
        bit = self.so.value()
        self.sck.on()
        utime.sleep_us(10)
        return bit


class NoThermocoupleAttached(Exception):
    """Raised when there is no thermocouple attached to MAX6675"""
    pass

