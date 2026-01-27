from micropython import const
from machine import SoftI2C, Pin
import binascii

_REGISTER_VCELL = const(0x02)
_REGISTER_SOC = const(0x04)
_REGISTER_MODE = const(0x06)
_REGISTER_VERSION = const(0x08)
_REGISTER_CONFIG = const(0x0c)
_REGISTER_COMMAND = const(0xfe)

_THRESHOLD_BITS = 0x1f  # 0b00011111
_SLEEP_BIT = 0x80    # 0b10000000
_ALERT_BITS = 0x20  # 0b00100000

class MAX17043:

    def __init__(self, i2c: SoftI2C):
        self.i2c = i2c
        self.address = (self.i2c.scan())[0]

    def __repr__(self):
        return f"MAX17043(address={self.address}, version=0x{self.version:04x}, compensation={self.compensation}, alert_threshold={self.alert_threshold}%)"

    def __str__(self):
        return f"v: {self.voltage} V, soc: {self.soc} %, alert: {self.alert} (threshold: {self.alert_threshold} %), sleep: {self.sleep}"

    def reset(self):
        self._write_reg(_REGISTER_COMMAND, binascii.unhexlify('0054'))

    def quick_start(self):
        self._write_reg(_REGISTER_MODE, binascii.unhexlify('4000'))

    def clear_alert(self):
        self._read_cfg_reg()

    def conf(self):
        return "{:08b} {:08b}".format(*self._read_cfg_reg())

    @property
    def sleep(self):
        return (self._read_cfg_reg())[1] & _SLEEP_BIT != 0

    @sleep.setter
    def sleep(self, value: bool):
        buf = bytearray(self._read_cfg_reg())
        buf[1] = (buf[1] | _SLEEP_BIT) if value else (buf[1] & ~_SLEEP_BIT)
        self._write_cfg_reg(buf)

    @property
    def voltage(self):
        buf = self._read_reg(_REGISTER_VCELL)
        return (buf[0] << 4 | buf[1] >> 4) /1000.0

    @property
    def soc(self):
        buf = self._read_reg(_REGISTER_SOC)
        return buf[0] + (buf[1] / 256.0)

    @property
    def alert(self):
        return (self._read_cfg_reg())[1] & _ALERT_BITS != 0

    @alert.setter
    def alert(self, value: bool):
        buf = bytearray(self._read_cfg_reg())
        if value:
            buf[1] = buf[1] | _ALERT_BITS
        else:
            buf[1] = buf[1] & (~_ALERT_BITS)
        self._write_cfg_reg(buf)

    @property
    def version(self):
        buf = self._read_reg(_REGISTER_VERSION)
        return (buf[0] << 8 ) | buf[1]

    @property
    def compensation(self):
        return self._read_cfg_reg()[0]

    @property
    def alert_threshold(self):
        return (_THRESHOLD_BITS + 1) - (self._read_cfg_reg()[1] & _THRESHOLD_BITS)

    @alert_threshold.setter
    def alert_threshold(self, threshold):
        raw = (_THRESHOLD_BITS + 1) - min(threshold, _THRESHOLD_BITS + 1)
        buf = bytearray(self._read_cfg_reg())
        buf[1] = (buf[1] & ~_THRESHOLD_BITS) | (raw & _THRESHOLD_BITS)
        self._write_cfg_reg(buf)

    def _read_reg(self, address):
        return self.i2c.readfrom_mem(self.address, address, 2)

    def _write_reg(self, address, buf):
        self.i2c.writeto_mem(self.address, address, buf)

    def _read_cfg_reg(self):
        return self._read_reg(_REGISTER_CONFIG)

    def _write_cfg_reg(self, buf):
        self._write_reg(_REGISTER_CONFIG, buf)


if __name__ == "__main__":
    from time import sleep
    battery = MAX17043(SoftI2C(scl=Pin(18), sda=Pin(9)))
    print(repr(battery))
    print(f"CONFIG: {battery.conf()}")

    while True:
        print(str(battery))
        sleep(2)
