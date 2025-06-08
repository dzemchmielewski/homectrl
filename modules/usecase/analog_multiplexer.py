from devices.desk.analog_multiplexer import AnalogMultiplexer

m = AnalogMultiplexer([14, 13, 47, 48][::-1], signal_pin=21, channels_range=16)

try:
    while True:
        print("")
        number = int(input("Number (0-{}): ".format(m.channels_range - 1)))
        m.set_on(number)
except KeyboardInterrupt:
    pass
