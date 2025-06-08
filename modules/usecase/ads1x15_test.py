from machine import SoftI2C, Pin
from time import sleep
from ads1x15 import ADS1X15Constants, ADS1X15

#   ADS1115_RANGE_6144  ->  +/- 6144 mV
#   ADS1115_RANGE_4096  ->  +/- 4096 mV
#   ADS1115_RANGE_2048  ->  +/- 2048 mV (default)
#   ADS1115_RANGE_1024  ->  +/- 1024 mV
#   ADS1115_RANGE_0512  ->  +/- 512 mV
#   ADS1115_RANGE_0256  ->  +/- 256 mV
# ads.set_voltage_range_mv(ADS1X15Constants.ADS1115_RANGE_6144)

#   ADS1115_COMP_0_1    ->  compares 0 with 1 (default)
#   ADS1115_COMP_0_3    ->  compares 0 with 3
#   ADS1115_COMP_1_3    ->  compares 1 with 03
#   ADS1115_COMP_2_3    ->  compares 2 with 3
#   ADS1115_COMP_0_GND  ->  compares 0 with GND
#   ADS1115_COMP_1_GND  ->  compares 1 with GND
#   ADS1115_COMP_2_GND  ->  compares 2 with GND
#   ADS1115_COMP_3_GND  ->  compares 3 with GND
# ads.set_compare_channels(ADS1X15Constants.ADS1115_COMP_0_GND)

#   ADS1115_ASSERT_AFTER_1  -> after 1 conversion
#   ADS1115_ASSERT_AFTER_2  -> after 2 conversions
#   ADS1115_ASSERT_AFTER_4  -> after 4 conversions
#   ADS1115_DISABLE_ALERT   -> disable comparator / alert pin (default)
#adc.setAlertPinMode(ADS1115_ASSERT_AFTER_1)

#   ADS1115_8_SPS
#   ADS1115_16_SPS
#   ADS1115_32_SPS
#   ADS1115_64_SPS
#   ADS1115_128_SPS (default)
#   ADS1115_250_SPS
#   ADS1115_475_SPS
#   ADS1115_860_SPS
# ads.set_conv_rate(ADS1X15Constants.ADS1115_128_SPS)

#   ADS1115_CONTINUOUS  ->  continuous mode
#   ADS1115_SINGLE     ->  single shot mode (default)
# ads.set_measure_mode(ADS1X15Constants.ADS1115_CONTINUOUS)

#   Choose maximum limit or maximum and minimum alert limit (window) in Volt - alert pin will
#   assert when measured values are beyond the maximum limit or outside the window
#   Upper limit first: setAlertLimit_V(MODE, maximum, minimum)
#   In max limit mode the minimum value is the limit where the alert pin assertion will be
#   cleared (if not latched)
#
#   ADS1115_MAX_LIMIT
#   ADS1115_WINDOW
#adc.setAlertModeAndLimit_V(ADS1115_MAX_LIMIT, 3.0, 1.5)

#   Enable or disable latch. If latch is enabled the alert pin will assert until the
#   conversion register is read (getResult functions). If disabled the alert pin assertion will be
#   cleared with next value within limits.
#
#   ADS1115_LATCH_DISABLED (default)
#   ADS1115_LATCH_ENABLED
#adc.setAlertLatch(ADS1115_LATCH_ENABLED)

#   Sets the alert pin polarity if active:
#
#   ADS1115_ACT_LOW  ->  active low (default)
#   ADS1115_ACT_HIGH ->  active high
#adc.setAlertPol(ADS1115_ACT_LOW)

#   With this function the alert pin will assert, when a conversion is ready.
#   In order to deactivate, use the setAlertLimit_V function
#adc.setAlertPinToConversionReady()

ads = ADS1X15(SoftI2C(scl=Pin(21), sda=Pin(20)))
ads.set_measure_mode(ADS1X15Constants.ADS1115_CONTINUOUS)
ads.set_compare_channels(ADS1X15Constants.ADS1115_COMP_0_GND)
ads.set_conv_rate(ADS1X15Constants.ADS1115_128_SPS)
ads.set_voltage_range_mv(ADS1X15Constants.ADS1115_RANGE_6144)


v = [0] * 4
while True:
    for i in range(4):
        ads.set_single_channel(i)
        v[i] = ads.get_result_mv()

    print("\t".join([f"A{i}: {v[i]:.6f}" for i in range(4)]))
    sleep(0.5)
