import smbus2

from .ahtx0 import AHT20
from .bmp280 import BMP280, BMP280_CASE_HANDHELD_DYN


class BMP_AHT:

    def __init__(self,
                 i2c_bus: smbus2.SMBus,
                 calibrate_temperature: float = 0.0,
                 calibrate_pressure: float = 0.0,
                 calibrate_humidity: float = 0.0):
        self.bmp = BMP280(i2c_bus, addr=0x77, use_case=BMP280_CASE_HANDHELD_DYN)
        self.aht = AHT20(i2c_bus)
        self.calibrate_temperature = calibrate_temperature
        self.calibrate_pressure = calibrate_pressure
        self.calibrate_humidity = calibrate_humidity

    @classmethod
    def from_bus(cls, bus_number: int = 1,
                 calibrate_temperature: float = 0.0,
                 calibrate_pressure: float = 0.0,
                 calibrate_humidity: float = 0.0):
        return BMP_AHT(smbus2.SMBus(bus_number), calibrate_temperature, calibrate_pressure, calibrate_humidity)

    @property
    def temperature(self):
        return round((self.bmp.temperature + self.aht.temperature) / 2, 1) + self.calibrate_temperature

    @property
    def pressure(self):
        return round(self.bmp.pressure / 100, 1) + self.calibrate_pressure

    @property
    def humidity(self):
        return round(self.aht.relative_humidity, 1) + self.calibrate_humidity

    def readings(self):
        return self.temperature, self.pressure, self.humidity
