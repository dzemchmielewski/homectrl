# SCK 8    17
# SDO 9    11
# SDI 10    12
# CS 20    13
# FLT 21
# DRDY 0

import time
from machine import SPI, Pin
from max31856 import Max31856

#DEV:
# spi = SPI(1, baudrate=1000000, polarity=1, sck=Pin(8), mosi=Pin(10), miso=Pin(9))
# cs = Pin(20, Pin.OUT)

#OWEN:
spi = SPI(1, baudrate=1000000, polarity=1, sck=Pin(17), mosi=Pin(12), miso=Pin(11))
cs = Pin(13, Pin.OUT)

max31856 = Max31856(spi, cs, 'K')

while True:
    tc = max31856.temperature(read_chip=True)
    cj = max31856.cold_junction()
    f, fs = max31856.faults()
    print(f"Temperatures: {tc:7.6f}\t{cj:7.6f}\t(roundings: {tc:3.1f}, {round(tc): 3d})\tfault: {f} {fs}")
    time.sleep(1)

