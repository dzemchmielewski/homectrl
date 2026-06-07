from board.boot import Boot
boot = Boot.get_instance(pin_notify=None, pin_notify_on_signal=0)
boot.load(wifi=False, lan=False, webrepl=False, time=False)
