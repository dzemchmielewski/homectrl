# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
import network
import utime
import machine


def _blink(pin, pattern):
    led_pin = machine.Pin(pin, machine.Pin.OUT)
    for s in pattern:
        led_pin.value(1)
        utime.sleep(s)
        led_pin.value(0)
        utime.sleep(s)


def wifi_setup():
    # wifi_ssid = ""
    # wifi_password = ""
    exec(open("credentials.py").read())

    station = network.WLAN(network.STA_IF)
    station.active(True)

    while not station.isconnected():
        print("Connecting to '{}'...".format(wifi_ssid))
        station.connect(wifi_ssid, wifi_password)
        utime.sleep(10)
    print("Connected! IP address: {}".format(station.ifconfig()[0]))


_blink(8, [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05])
wifi_setup()
webrepl.start()
machine.Pin(8, machine.Pin.OUT).value(1)
