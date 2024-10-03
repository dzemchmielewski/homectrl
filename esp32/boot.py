# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
import network
import utime
import time
import machine
import os

allow_blink = True

def _blink(pin, pattern):
    if allow_blink:
        led_pin = machine.Pin(pin, machine.Pin.OUT)
        for s in pattern:
            led_pin.value(1)
            utime.sleep(s)
            led_pin.value(0)
            utime.sleep(s)


def blink(reverse = False):
    if allow_blink:
        pattern = [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05]
        if reverse:
            pattern.reverse()
        _blink(8, pattern)


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


def set_time():
    import ntptime
    import utime
    ntptime.settime()
    (year, month, mday, hour, minute, second, weekday, yearday) = utime.localtime(utime.time() + 2 * 60 * 60)
    machine.RTC().datetime((year, month, mday, 0, hour, minute, second, 0))


def get_credentials() -> (str, str):
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
    return wifi_ssid, wifi_password


def setup_wifi(ssid, password):
    network.country("PL")
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.disconnect()

    while not wifi.isconnected():
        timeout = 30000
        blink()
        wifi.connect(ssid, password)
        while timeout > 0:
            if not wifi.isconnected():
                time.sleep_ms(200)
                timeout = timeout - 200
            else:
                break
        if timeout <= 0:
            blink(True)
    print("Connected! ifconfig: {}".format(wifi.ifconfig()))
    return wifi


wifi_ssid, wifi_password = get_credentials()
wifi = setup_wifi(wifi_ssid, wifi_password)

try:
    set_time()
except BaseException:
    pass

if allow_blink:
    machine.Pin(8, machine.Pin.OUT).value(1)
webrepl.start()
