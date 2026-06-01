from machine import Pin
from board.boot import Boot

# 22 - blue LED on the board (notify_on_signal = 0)
# 25 - blue LED - custom one (notify_on_signal = 1)
boot = Boot.get_instance(pin_notify=25, pin_notify_on_signal=1)

red_btn = Pin(35, Pin.IN, Pin.PULL_DOWN)

if red_btn.value() == 1:
    # when button is pressed on boot, load wifi, webrepl
    # to enter maintenance mode
    boot.load(wifi=True, lan=False, webrepl=True, time=True)
    # boot.pin_notify.value(0)

else:
    boot.load(wifi=False, lan=False, webrepl=False, time=False)
