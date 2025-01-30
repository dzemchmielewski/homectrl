"""Sample code and test for barbudor_ina3221"""

import time
import sys
from machine import Pin, SoftI2C
from modules.ina3221 import *

bus  = SoftI2C(scl=Pin(11), sda=Pin(12), freq=400000)

# INA3221.IS_FULL_API = False
ina = [INA3221(bus, i2c_addr=0x40 + i) for i in range(4)]
for i in range(4):
    if INA3221.IS_FULL_API:
        ina[i].update(reg=C_REG_CONFIG,
                           mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
                           value=C_AVERAGING_128_SAMPLES | C_VBUS_CONV_TIME_8MS | C_SHUNT_CONV_TIME_8MS | C_MODE_SHUNT_AND_BUS_CONTINOUS)
    for c in range(3):
        ina[i].enable_channel(c + 1)

ina3221 = ina[2]
while True:
    if INA3221.IS_FULL_API: # is_ready available only in "full" variant
        while not ina3221.is_ready:
            print(".",end='')
            time.sleep(0.1)
        print("")

    print("------------------------------")
    line_title =         "Measurement   "
    line_psu_voltage =   "PSU voltage   "
    line_load_voltage =  "Load voltage  "
    line_shunt_voltage = "Shunt voltage "
    line_current =       "Current       "

    for chan in range(1,4):
        if ina3221.is_channel_enabled(chan):
            #
            bus_voltage = ina3221.bus_voltage(chan)
            shunt_voltage = ina3221.shunt_voltage(chan)
            current = ina3221.current(chan)
            #
            line_title +=         "| Chan#{:d}      ".format(chan)
            line_psu_voltage +=   "| {:6.3f}    V ".format(bus_voltage + shunt_voltage)
            line_load_voltage +=  "| {:6.3f}    V ".format(bus_voltage)
            line_shunt_voltage += "| {:9.6f} V ".format(shunt_voltage)
            line_current +=       "| {:9.6f} A ".format(current)

    print(line_title)
    print(line_psu_voltage)
    print(line_load_voltage)
    print(line_shunt_voltage)
    print(line_current)

    time.sleep(1.0)
