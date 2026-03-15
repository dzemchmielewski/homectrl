from board.boot import Boot
import timesync
from ds3231 import DS3231
from machine import SoftI2C, Pin

ds = DS3231(SoftI2C(sda=Pin(5), scl=Pin(6)))
Boot.setup_time = lambda x : timesync.rtc_to_sys(ds.datetime)

boot = Boot.get_instance(pin_notify=None, pin_notify_on_signal=0)
boot.load(wifi=True, lan=False, webrepl=True, time=True)
