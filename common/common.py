import sys
from os import uname

UNAME = uname()
BOARD = UNAME.sysname
MACHINE = UNAME.machine
loaded = False

if BOARD == "WiPy" or BOARD == "LoPy" or BOARD == "FiPy":
    # Todo...
    pass

elif BOARD == "esp8266" or BOARD == "esp32":
    # Todo...
    pass

elif BOARD == 'rp2':
    # Raspberry Pico
    from common.platform.rp2pico import CommonGPIO, log_entry_prefix, time_ms
    loaded = True

elif BOARD == "Linux":
    # Linux:
    # from datetime import datetime
    from common.platform.linux import log_entry_prefix, time_ms

    # Linux without GPIO:
    if MACHINE == "x86_64":
        from common.platform.none_gpio import CommonGPIO
        loaded = True

    # Linux, with GPIO, like Raspberry PI
    elif MACHINE == "armv7l":
        from common.platform.rpi_gpio import CommonGPIO
        loaded = True

else:
    raise RuntimeError("Unsupported platform")


class Metering:
    def __init__(self, steps_per_loop=1):
        self.steps_per_loop = steps_per_loop
        self._step = 0
        self.start_timer = time_ms()

    def start(self):
        self.start_timer = time_ms()
        self._step = 0

    def step(self, step=1) -> (int, float):
        self._step += step
        if self._step >= self.steps_per_loop:
            return self.loop()
        return None

    def loop(self) -> (int, float):
        end = time_ms()
        result = (self._step, end - self.start_timer)
        self.start_timer = time_ms()
        self._step = 0
        return result


class Common:
    def __init__(self, name, debug=False, metering=False):
        self.name = name
        self.enableDebug = debug
        self.enableMetering = metering
        self.metering = None
        self.gpio = CommonGPIO()

    def debug(self, message, prefix=None):
        if self.enableDebug:
            if prefix is None:
                prefix = log_entry_prefix()
            print("[{}][{}][DEBUG] {}".format(prefix, self.name, message))

    def log(self, msg, prefix=None):
        if prefix is None:
            prefix = log_entry_prefix()
        print("[{}][{}] {}".format(prefix, self.name, msg))
        if BOARD == "Linux":
            sys.stdout.flush()

    def input(self, msg, prefix=None):
        if prefix is None:
            prefix = log_entry_prefix()
        return input("[{}][{}] {}".format(prefix, self.name, msg))

    def metering_start(self):
        if self.enableMetering:
            self.metering = Metering()
        return self.metering

    def metering_print(self, message):
        if self.enableMetering:
            self.log("[METERING] {} {}".format(message, self.metering.step()))

    @staticmethod
    def format_uptime(uptime):
        (minutes, seconds) = divmod(uptime, 60)
        (hours, minutes) = divmod(minutes, 60)
        (days, hours) = divmod(hours, 24)
        result = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        if days:
            result = "{:d} days ".format(days) + " " + result
        return result


if __name__ == "__main__":
    c = Common("test", True)
    c.log("test")
    c.debug("debug")
    c.log("end")
