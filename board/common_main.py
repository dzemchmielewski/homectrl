import machine
import utime


def _blink(pin=25, pattern = [0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05]):
    led_pin = machine.Pin(pin, machine.Pin.OUT)
    for s in pattern:
        led_pin.value(1)
        utime.sleep(s)
        led_pin.value(0)
        utime.sleep(s)

