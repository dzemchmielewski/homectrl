# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
import network
import utime
import machine
import os


def _blink(pin, pattern):
    led_pin = machine.Pin(pin, machine.Pin.OUT)
    for s in pattern:
        led_pin.value(1)
        utime.sleep(s)
        led_pin.value(0)
        utime.sleep(s)


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


def wifi_setup():
    credentials = "credentials.py"
    if file_exists(credentials):
        print("Reading {} file...".format(credentials))
        from credentials import wifi_ssid, wifi_password
        print("SSID: {}".format(wifi_ssid))
    else:
        wifi_ssid = input("SSID: ").strip()
        wifi_password = input("Password: ").strip()
        with open(credentials, "w") as f:
            f.write("wifi_ssid = \"{}\"\nwifi_password = \"{}\"\n".format(wifi_ssid, wifi_password))

    station = network.WLAN(network.STA_IF)
    station.active(True)

    while not station.isconnected():
        _blink(8, [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05])
        print("Connecting to '{}'...".format(wifi_ssid))
        station.connect(wifi_ssid, wifi_password)
        utime.sleep(10)
    print("Connected! IP address: {}".format(station.ifconfig()[0]))

wifi_setup()
machine.Pin(8, machine.Pin.OUT).value(1)
webrepl.start()
