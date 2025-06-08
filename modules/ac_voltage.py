from ads1x15 import ADS1X15, ADS1X15Constants
from machine import SoftI2C, Pin
import math
import time

class ACVoltage(ADS1X15):
    def __init__(self, i2c: SoftI2C, alert_pin: int, channel: int, address = ADS1X15Constants.ADS1115_DEFAULT_ADDR):
        super().__init__(i2c, address)
        self.set_voltage_range_mv(ADS1X15Constants.ADS1115_RANGE_6144)
        self.set_compare_channels(ADS1X15Constants.ADS1115_COMP_0_GND + (channel * ADS1X15Constants.ADS1115_COMP_INC))
        self.set_conv_rate(ADS1X15Constants.ADS1115_860_SPS)
        self.set_measure_mode(ADS1X15Constants.ADS1115_CONTINUOUS)

        self.set_alert_pin_mode(ADS1X15Constants.ADS1115_ASSERT_AFTER_1)
        self.set_alert_pol(ADS1X15Constants.ADS1115_ACT_HIGH)
        self.set_alert_pin_to_conversion_ready()

        self.alert_pin = Pin(alert_pin, Pin.IN, Pin.PULL_DOWN)
        self.alert_pin.irq(trigger=Pin.IRQ_RISING, handler=self.alert_handler)
        self.alert = False

        self.samples = [0.0] * 200
        self.ac_samples = [0.0] * 200

    def alert_handler(self, alert_pin):
        self.alert = True

    @staticmethod
    def _mean(array, count):
        mean = 0
        for i in range(count):
            mean += array[i]
        return mean / count

    @staticmethod
    def _rms(array, count):
        sum2 = 0
        for i in range(count):
            sum2 += array[i]**2
        return math.sqrt(sum2 / count)

    # def read_single_shot(self, num_periods=10, frequency=50):
    #     measure_time_us = (1_000_000/frequency) * num_periods
    #     count = 0
    #     start = time.ticks_us()
    #     while time.ticks_diff(time.ticks_us(), start) < measure_time_us:
    #         self.start_single_measurement()
    #         while self.is_busy():
    #             pass
    #         self.samples[count] = self.get_result_mv()
    #         count += 1
    #     mean = self._mean(self.samples, count)
    #     for i in range(count):
    #         self.ac_samples[i] = self.samples[i] - mean
    #     rms = self._rms(self.ac_samples, count)
    #
    #     # # Not required section:
    #     # max_samples, min_samples = -999999999, 999999999
    #     # for i in range(count):
    #     #     max_samples = max(max_samples, self.samples[i])
    #     #     min_samples = min(min_samples, self.samples[i])
    #     # max_ac_samples, min_ac_samples = -999999999, 999999999
    #     # for i in range(count):
    #     #     max_ac_samples = max(max_ac_samples, self.ac_samples[i])
    #     #     min_ac_samples = min(min_ac_samples, self.ac_samples[i])
    #     #
    #     # print(f"DC mean: {mean:.4f}, count: {count}, max: {max_samples:.4f}, min: {min_samples:.4f}")
    #     # print(f"AC RMS: {rms:.4f}, mean: {self._mean(self.ac_samples, count)}, max: {max_ac_samples:.4f}, min: {min_ac_samples:.4f}")
    #     #
    #     # return rms

    def read(self, calibration = -2):
        measure_time_us = 200_000
        count = 0
        start = time.ticks_us()
        while time.ticks_diff(time.ticks_us(), start) < measure_time_us and count < len(self.samples):
            while not self.alert and time.ticks_diff(time.ticks_us(), start) < measure_time_us:
                pass
            self.alert = False
            self.samples[count] = self.get_result_mv()
            count += 1

        mean = self._mean(self.samples, count)
        for i in range(count):
            self.ac_samples[i] = self.samples[i] - mean
        rms = self._rms(self.ac_samples, count)

        # Not required section:
        max_samples, min_samples = -999999999, 999999999
        for i in range(count):
            max_samples = max(max_samples, self.samples[i])
            min_samples = min(min_samples, self.samples[i])
        max_ac_samples, min_ac_samples = -999999999, 999999999
        for i in range(count):
            max_ac_samples = max(max_ac_samples, self.ac_samples[i])
            min_ac_samples = min(min_ac_samples, self.ac_samples[i])

        print(f"DC mean: {mean:.4f}, count: {count}, max: {max_samples:.4f}, min: {min_samples:.4f}, diff: {max_samples - min_samples:.4f}")
        print(f"AC RMS: {rms:.4f}, mean: {self._mean(self.ac_samples, count)}, max: {max_ac_samples:.4f}, min: {min_ac_samples:.4f} diff: {max_ac_samples - min_ac_samples:.4f}")

        return rms + calibration

if __name__ == "__main__":
    ads = ACVoltage(SoftI2C(scl=Pin(2), sda=Pin(1)), 21, 0)
    try:
        while True:
            v = ads.read()
            amps = v / 100
            print(f"Voltage: {v:.4f}mV, amps: {amps:.4f}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("EXIT")