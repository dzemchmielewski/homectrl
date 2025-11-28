"""Sample code and test for barbudor_ina3221"""

import time
import sys
from machine import Pin, SoftI2C
from ina3221 import *

bus  = SoftI2C(scl=Pin(3), sda=Pin(2), freq=400000)

# INA3221.IS_FULL_API = False
ina = INA3221(bus, i2c_addr=0x40)
if INA3221.IS_FULL_API:
    ina.update(reg=C_REG_CONFIG,
                       mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
                       value=C_AVERAGING_128_SAMPLES | C_VBUS_CONV_TIME_8MS | C_SHUNT_CONV_TIME_8MS | C_MODE_SHUNT_AND_BUS_CONTINOUS)

channels = [1,2,3]
#channels = [3]
for c in channels:
    ina.enable_channel(c)

time.sleep(2)

for i in range(3):
    print("Channel {:d} enabled: {}".format(i+1, ina.is_channel_enabled(i+1)))

while True:
    if INA3221.IS_FULL_API: # is_ready available only in "full" variant
        while not ina.is_ready:
            print(".",end='')
            time.sleep(0.1)
        print("")

    print("------------------------------")
    line_title =         "Measurement   "
    line_psu_voltage =   "PSU voltage   "
    line_load_voltage =  "Load voltage  "
    line_shunt_voltage = "Shunt voltage "
    line_current =       "Current       "

    for chan in channels:
        #if ina3221.is_channel_enabled(chan):
            #
            bus_voltage = ina.bus_voltage(chan)
            shunt_voltage = ina.shunt_voltage(chan)
            current = ina.current(chan)
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
