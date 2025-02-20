from machine import SoftI2C, Pin

from toolbox.ahtx0 import AHT20
from toolbox.bmp280 import BMP280, BMP280_CASE_HANDHELD_DYN


class BMP_AHT:

    def __init__(self, i2c_bus: SoftI2C):
        self.bmp = BMP280(i2c_bus, addr=0x77, use_case=BMP280_CASE_HANDHELD_DYN)
        self.aht = AHT20(i2c_bus)

    @classmethod
    def from_pins(cls, scl: int, sda: int):
        return BMP_AHT(SoftI2C(Pin(scl), Pin(sda)))

    @property
    def temperature(self):
        return round((self.bmp.temperature + self.aht.temperature) / 2, 1)

    @property
    def pressure(self):
        return round(self.bmp.pressure / 100, 1)

    @property
    def humidity(self):
        return round(self.aht.relative_humidity, 1)

    def readings(self):
        return self.temperature, self.pressure, self.humidity
