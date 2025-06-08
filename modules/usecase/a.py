#####################################################################################
# Example program for the ADS1115_mPy module
#
# This program shows how you can use the alert pin as conversion ready alert pin.
# It works in continuous mode as well as in single shot mode.
# Please note that you need to enable the alert pin with setAlertPinMode. Choose any
# parameter except ADS1115_DISABLE_ALERT.
#
# Further information can be found on (currently only for the Arduino version):
# https://wolles-elektronikkiste.de/ads1115 (German)
# https://wolles-elektronikkiste.de/en/ads1115-a-d-converter-with-amplifier (English)
#
#####################################################################################

from machine import I2C, Pin, SoftI2C
from time import sleep
import struct
from time import sleep_ms
__ADS1115_CONV_REG      = 0x00     #Conversion Register
__ADS1115_CONFIG_REG    = 0x01     #Configuration Register
__ADS1115_LO_THRESH_REG = 0x02     #Low Threshold Register
__ADS1115_HI_THRESH_REG = 0x03     #High Threshold Register

__ADS1115_DEFAULT_ADDR  = 0x48
__ADS1115_REG_RESET_VAL = 0x8583
__ADS1115_REG_FACTOR    = 0x7FFF

__ADS1115_BUSY          = 0x0000
__ADS1115_START_ISREADY = 0x8000

__ADS1115_COMP_INC = 0x1000

ADS1115_ASSERT_AFTER_1 = 0x0000
ADS1115_ASSERT_AFTER_2 = 0x0001
ADS1115_ASSERT_AFTER_4 = 0x0002
ADS1115_DISABLE_ALERT  = 0x0003
ADS1015_ASSERT_AFTER_1 = ADS1115_ASSERT_AFTER_1
ADS1015_ASSERT_AFTER_2 = ADS1115_ASSERT_AFTER_2
ADS1015_ASSERT_AFTER_4 = ADS1115_ASSERT_AFTER_4
ADS1015_DISABLE_ALERT  = ADS1115_DISABLE_ALERT


ADS1115_LATCH_DISABLED = 0x0000
ADS1115_LATCH_ENABLED  = 0x0004
ADS1015_LATCH_DISABLED = 0x0000
ADS1015_LATCH_ENABLED  = 0x0004

ADS1115_ACT_LOW  = 0x0000
ADS1115_ACT_HIGH = 0x0008
ADS1015_ACT_LOW  = ADS1115_ACT_LOW
ADS1015_ACT_HIGH = ADS1115_ACT_HIGH

ADS1115_MAX_LIMIT = 0x0000
ADS1115_WINDOW    = 0x0010
ADS1015_MAX_LIMIT = ADS1115_MAX_LIMIT
ADS1015_WINDOW    = ADS1115_WINDOW

ADS1115_8_SPS   = 0x0000
ADS1115_16_SPS  = 0x0020
ADS1115_32_SPS  = 0x0040
ADS1115_64_SPS  = 0x0060
ADS1115_128_SPS = 0x0080
ADS1115_250_SPS = 0x00A0
ADS1115_475_SPS = 0x00C0
ADS1115_860_SPS = 0x00E0
ADS1015_128_SPS  = ADS1115_8_SPS
ADS1015_250_SPS  = ADS1115_16_SPS
ADS1015_490_SPS  = ADS1115_32_SPS
ADS1015_920_SPS  = ADS1115_64_SPS
ADS1015_1600_SPS = ADS1115_128_SPS
ADS1015_2400_SPS = ADS1115_250_SPS
ADS1015_3300_SPS = ADS1115_475_SPS
ADS1015_3300_SPS_2 = ADS1115_860_SPS

ADS1115_RANGE_6144  = 0x0000
ADS1115_RANGE_4096  = 0x0200
ADS1115_RANGE_2048  = 0x0400
ADS1115_RANGE_1024  = 0x0600
ADS1115_RANGE_0512  = 0x0800
ADS1115_RANGE_0256  = 0x0A00
ADS1015_RANGE_6144  = ADS1115_RANGE_6144
ADS1015_RANGE_4096  = ADS1115_RANGE_4096
ADS1015_RANGE_2048  = ADS1115_RANGE_2048
ADS1015_RANGE_1024  = ADS1115_RANGE_1024
ADS1015_RANGE_0512  = ADS1115_RANGE_0512
ADS1015_RANGE_0256  = ADS1115_RANGE_0256

ADS1115_COMP_0_1   = 0x0000
ADS1115_COMP_0_3   = 0x1000
ADS1115_COMP_1_3   = 0x2000
ADS1115_COMP_2_3   = 0x3000
ADS1115_COMP_0_GND = 0x4000
ADS1115_COMP_1_GND = 0x5000
ADS1115_COMP_2_GND = 0x6000
ADS1115_COMP_3_GND = 0x7000
ADS1015_COMP_0_1   = ADS1115_COMP_0_1
ADS1015_COMP_0_3   = ADS1115_COMP_0_3
ADS1015_COMP_1_3   = ADS1115_COMP_1_3
ADS1015_COMP_2_3   = ADS1115_COMP_2_3
ADS1015_COMP_0_GND = ADS1115_COMP_0_GND
ADS1015_COMP_1_GND = ADS1115_COMP_1_GND
ADS1015_COMP_2_GND = ADS1115_COMP_2_GND
ADS1015_COMP_3_GND = ADS1115_COMP_3_GND

ADS1115_CONTINUOUS = 0x0000
ADS1115_SINGLE     = 0x0100
ADS1015_CONTINUOUS = ADS1115_CONTINUOUS
ADS1015_SINGLE     = ADS1115_SINGLE

class ADS1115(object):
    __autoRangeMode = False
    __voltageRange = 2048
    __measureMode = ADS1115_SINGLE

    def __init__(self, address = __ADS1115_DEFAULT_ADDR, i2c = None):
        self.__address = address
        if i2c is None:
            try:
                i2c = I2C(0)
            except:
                i2c = I2C()
        self.__i2c = i2c
        try:
            self.reset()
        except OSError:  # I2C bus error:
            raise ValueError("Can't connect to the ADS1115. Check wiring, address, etc.")

        self.setVoltageRange_mV(ADS1115_RANGE_2048)
        self.__writeADS1115(__ADS1115_LO_THRESH_REG, 0x8000)
        self.__writeADS1115(__ADS1115_HI_THRESH_REG, 0x7FFF)
        self.__measureMode = ADS1115_SINGLE
        self.__autoRangeMode = False

    def setAlertPinMode(self, mode):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0x8003)
        currentConfReg |= mode
        self.__setConfReg(currentConfReg)

    def setAlertLatch(self, latch):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0x8004)
        currentConfReg |= latch
        self.__setConfReg(currentConfReg)

    def setAlertPol(self, polarity):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0x8008)
        currentConfReg |= polarity
        self.__setConfReg(currentConfReg)

    def setAlertModeAndLimit_V(self, mode, hiThres, loThres):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0x8010)
        currentConfReg |= mode
        self.__setConfReg(currentConfReg)
        alertLimit = self.__calcLimit(hiThres)
        self.__writeADS1115(__ADS1115_HI_THRESH_REG, alertLimit)
        alertLimit = self.__calcLimit(loThres)
        self.__writeADS1115(__ADS1115_LO_THRESH_REG, alertLimit)

    def __calcLimit(self, rawLimit):
        limit = int((rawLimit * __ADS1115_REG_FACTOR / self.__voltageRange) * 1000)
        if limit > 32767:
            limit -= 65536
        return limit

    def reset(self):
        return self.__setConfReg(__ADS1115_REG_RESET_VAL)

    def setVoltageRange_mV(self, newRange):
        currentVoltageRange = self.__voltageRange
        currentConfReg = self.__getConfReg()
        currentRange = (currentConfReg >> 9) & 7
        currentAlertPinMode = currentConfReg & 3

        self.setMeasureMode(ADS1115_SINGLE)

        if newRange == ADS1115_RANGE_6144:
            self.__voltageRange = 6144;
        elif newRange == ADS1115_RANGE_4096:
             self.__voltageRange = 4096;
        elif newRange == ADS1115_RANGE_2048:
            self.__voltageRange = 2048;
        elif newRange == ADS1115_RANGE_1024:
            self.__voltageRange = 1024;
        elif newRange == ADS1115_RANGE_0512:
            self.__voltageRange = 512;
        elif newRange == ADS1115_RANGE_0256:
            self.__voltageRange = 256;

        if (currentRange != newRange) and (currentAlertPinMode != ADS1115_DISABLE_ALERT):
            alertLimit = self.__readADS1115(__ADS1115_HI_THRESH_REG)
            alertLimit = alertLimit * (currentVoltageRange / self.__voltageRange)
            self.__writeADS1115(__ADS1115_HI_THRESH_REG, alertLimit)
            alertLimit = self.__readADS1115(__ADS1115_LO_THRESH_REG)
            alertLimit = alertLimit * (currentVoltageRange / self.__voltageRange)
            self.__writeADS1115(__ADS1115_LO_THRESH_REG, alertLimit)

        currentConfReg &= ~(0x8E00)
        currentConfReg |= newRange
        self.__setConfReg(currentConfReg)
        rate = self.__getConvRate()
        self.__delayAccToRate(rate)

    def setAutoRange(self):
        currentConfReg = self.__getConfReg()
        self.setVoltageRange_mV(ADS1115_RANGE_6144)

        if self.__measureMode == ADS1115_SINGLE:
            self.setMeasureMode(ADS1115_CONTINUOUS)
            convRate = self.__getConvRate()
            self.__delayAccToRate(convRate)

        rawResult = abs(self.__getConvReg())
        optRange = ADS1115_RANGE_6144

        if rawResult < 1093:
            optRange = ADS1115_RANGE_0256
        elif rawResult < 2185:
            optRange = ADS1115_RANGE_0512
        elif rawResult < 4370:
            optRange = ADS1115_RANGE_1024
        elif rawResult < 8738:
            optRange = ADS1115_RANGE_2048
        elif rawResult < 17476:
            optRange = ADS1115_RANGE_4096

        self.__setConfReg(currentConfReg)
        self.setVoltageRange_mV(optRange)

    def setPermanentAutoRangeMode(self, autoMode):
        if autoMode:
            self.__autoRangeMode = True
        else:
            self.__autoRangeMode = False

    def setMeasureMode(self, mMode):
        currentConfReg = self.__getConfReg()
        self.__measureMode = mMode
        currentConfReg &= ~(0x8100)
        currentConfReg |= mMode
        self.__setConfReg(currentConfReg)

    def setCompareChannels(self, compChannels):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0xF000)
        currentConfReg |= compChannels
        self.__setConfReg(currentConfReg)

        if not (currentConfReg & 0x0100):  # if not single shot mode
            convRate = self.__getConvRate()
            for i in range(2):
                self.__delayAccToRate(convRate)

    def setSingleChannel(self, channel):
        if channel >= 4:
            return
        self.setCompareChannels((ADS1115_COMP_0_GND + ADS1115_COMP_INC) * channel)

    def isBusy(self):
        currentConfReg = self.__getConfReg()
        return not((currentConfReg>>15) & 1)

    def startSingleMeasurement(self):
        currentConfReg = self.__getConfReg()
        currentConfReg |= (1 << 15)
        self.__setConfReg(currentConfReg)

    def getResult_V(self):
        return self.getResult_mV()/1000

    def getResult_mV(self):
        rawResult = self.getRawResult()
        return rawResult * self.__voltageRange / __ADS1115_REG_FACTOR

    def getRawResult(self):
        rawResult = self.__getConvReg()

        if self.__autoRangeMode:
            if (abs(rawResult) > 26214) and (self.__voltageRange != 6144): # 80%
                self.setAutoRange()
                rawResult = self.__getConvReg()
            elif (abs(rawResult) < 9800) and (self.__voltageRange != 256):  # 30%
                self.setAutoRange()
                rawResult = self.__getConvReg()

        return rawResult

    def __getConvReg(self):
        rawResult = self.__readADS1115(__ADS1115_CONV_REG)
        if rawResult > 32767:
            rawResult -= 65536
        return rawResult

    def getResultWithRange(self, minLimit, maxLimit):
        rawResult = self.getRawResult()
        result = rawResult * (maxLimit - minLimit) / 65536
        return result

    def getResultWithRangeAndMaxVolt(self, minLimit, maxLimit, maxMillivolt):
        result = self.getResultWithRange(minLimit, maxLimit)
        result = result * self.__voltageRange / maxMillivolt
        return result

    def getVoltageRange_mV(self):
        return self.__voltageRange

    def setAlertPinToConversionReady(self):
        self.__writeADS1115(__ADS1115_LO_THRESH_REG, (0<<15))
        self.__writeADS1115(__ADS1115_HI_THRESH_REG, (1<<15))

    def clearAlert(self):
        self.__readADS1115(__ADS1115_CONV_REG)

    def __setConfReg(self, regVal):
        self.__writeADS1115(__ADS1115_CONFIG_REG, regVal)

    def __getConfReg(self):
        return self.__readADS1115(__ADS1115_CONFIG_REG)

    def __getConvRate(self):
        currentConfReg = self.__getConfReg()
        return (currentConfReg & 0xE0)

    def setConvRate(self, rate):
        currentConfReg = self.__getConfReg()
        currentConfReg &= ~(0x80E0)
        currentConfReg |= rate
        self.__setConfReg(currentConfReg)

    def __delayAccToRate(self, rate):
        if rate == ADS1115_8_SPS:
            sleep_ms(130)
        elif rate == ADS1115_16_SPS:
            sleep_ms(65)
        elif rate == ADS1115_32_SPS:
            sleep_ms(32)
        elif rate == ADS1115_64_SPS:
            sleep_ms(16)
        elif rate == ADS1115_128_SPS:
            sleep_ms(8)
        elif rate == ADS1115_250_SPS:
            sleep_ms(4)
        elif rate == ADS1115_475_SPS:
            sleep_ms(3)
        elif rate == ADS1115_860_SPS:
            sleep_ms(2)

    def __writeADS1115(self, reg, val):
        self.__i2c.writeto_mem(self.__address, reg, self.__toBytearray(val))

    def __readADS1115(self, reg):
        regVal = self.__i2c.readfrom_mem(self.__address, reg, 2)
        return self.__bytesToInt(regVal)

    def __toBytearray(self, intVal):
#        return bytearray(intVal.to_bytes(2, 'big'))
        return struct.pack('>i',intVal)[2:]

    def __bytesToInt(self, bytesToConvert):
        intVal = int.from_bytes(bytesToConvert, 'big') # "big" = MSB at beginning
        return intVal

class ADS1015(ADS1115):
     def __init__(self, address = __ADS1115_DEFAULT_ADDR, i2c = None):
        super().__init__(address, i2c)




ADS1115_ADDRESS = 0x48

adc = ADS1115(ADS1115_ADDRESS, i2c=SoftI2C(scl=Pin(21), sda=Pin(20)))

alertPin = Pin(10, Pin.IN, Pin.PULL_DOWN)
alert = False

def alert_handler(alertPin):
    global alert
    alert = True

alertPin.irq(trigger=Pin.IRQ_RISING, handler=alert_handler)

#     Set the voltage range of the ADC to adjust the gain:
#     Please note that you must not apply more than VDD + 0.3V to the input pins!
#     ADS1115_RANGE_6144  ->  +/- 6144 mV
#     ADS1115_RANGE_4096  ->  +/- 4096 mV
#     ADS1115_RANGE_2048  ->  +/- 2048 mV (default)
#     ADS1115_RANGE_1024  ->  +/- 1024 mV
#     ADS1115_RANGE_0512  ->  +/- 512 mV
#     ADS1115_RANGE_0256  ->  +/- 256 mV
adc.setVoltageRange_mV(ADS1115_RANGE_6144)

#     Set the inputs to be compared:
#     ADS1115_COMP_0_1    ->  compares 0 with 1 (default)
#     ADS1115_COMP_0_3    ->  compares 0 with 3
#     ADS1115_COMP_1_3    ->  compares 1 with 3
#     ADS1115_COMP_2_3    ->  compares 2 with 3
#     ADS1115_COMP_0_GND  ->  compares 0 with GND
#     ADS1115_COMP_1_GND  ->  compares 1 with GND
#     ADS1115_COMP_2_GND  ->  compares 2 with GND
#     ADS1115_COMP_3_GND  ->  compares 3 with GND
adc.setCompareChannels(ADS1115_COMP_0_GND)

#     Set number of conversions after which the alert pin will assert
#     - or you can disable the alert:
#     ADS1115_ASSERT_AFTER_1  -> after 1 conversion
#     ADS1115_ASSERT_AFTER_2  -> after 2 conversions
#     ADS1115_ASSERT_AFTER_4  -> after 4 conversions
#     ADS1115_DISABLE_ALERT   -> disable comparator / alert pin (default)
adc.setAlertPinMode(ADS1115_ASSERT_AFTER_1)

#     Set the conversion rate in SPS (samples per second)
#     Options should be self-explaining:
#     ADS1115_8_SPS
#     ADS1115_16_SPS
#     ADS1115_32_SPS
#     ADS1115_64_SPS
#     ADS1115_128_SPS (default)
#     ADS1115_250_SPS
#     ADS1115_475_SPS
#     ADS1115_860_SPS
adc.setConvRate(ADS1115_8_SPS)

#     Set continuous or single shot mode:
#     ADS1115_CONTINUOUS  ->  continuous mode
#     ADS1115_SINGLE     ->  single shot mode (default)
adc.setMeasureMode(ADS1115_SINGLE)

#     Choose maximum limit or maximum and minimum alert limit (window) in volts - alert pin will
#     assert when measured values are beyond the maximum limit or outside the window
#     Upper limit first: setAlertLimit_V(MODE, maximum, minimum)
#     In max limit mode the minimum value is the limit where the alert pin assertion will be
#     be cleared (if not latched).
#     ADS1115_MAX_LIMIT
#     ADS1115_WINDOW
# adc.setAlertModeAndLimit_V(ADS1115_MAX_LIMIT, 3.0, 1.5)

#     Enable or disable latch. If latch is enabled the alert pin will assert until the
#     conversion register is read (getResult functions). If disabled the alert pin assertion
#     will be cleared with next value within limits.
#     ADS1115_LATCH_DISABLED (default)
#     ADS1115_LATCH_ENABLED
# adc.setAlertLatch(ADS1115_LATCH_ENABLED)

#     Sets the alert pin polarity if active:
#     ADS1115_ACT_LOW  ->  active low (default)
#     ADS1115_ACT_HIGH ->  active high
adc.setAlertPol(ADS1115_ACT_HIGH)

#     With this function the alert pin will assert, when a conversion is ready.
#     In order to deactivate, use the setAlertLimit_V function
adc.setAlertPinToConversionReady()

print("ADS1115 Example Sketch - Single Shot, Conversion Ready Alert Pin controlled");
print()

#     In this example I measure 32 times before the result is output. This is only to slow down
#     the output rate. You don't have to read 32 times, of course.I want to show that the output
#     rate is controlled by the conversion ready alerts and not by a sleep.

counter = [0]
while True:
    if alert:
        counter[0] += 1
        alert = False
        if counter[0]==32:  # counter is 32, conversion rate is 8 SPS --> 4s
            voltage = adc.getResult_V()
            print("Channel 0 vs GND [V]: {:<4.2f}".format(voltage))
            print("-------------------------------")
            counter[0] = 0
    adc.startSingleMeasurement()