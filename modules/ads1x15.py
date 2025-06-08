#!/usr/bin/python
import math
import struct
import time
from time import sleep_ms
from machine import SoftI2C


class ADS1X15Constants:
    ADS1115_CONV_REG      = 0x00     #Conversion Register
    ADS1115_CONFIG_REG    = 0x01     #Configuration Register
    ADS1115_LO_THRESH_REG = 0x02     #Low Threshold Register
    ADS1115_HI_THRESH_REG = 0x03     #High Threshold Register

    ADS1115_DEFAULT_ADDR  = 0x48
    ADS1115_REG_RESET_VAL = 0x8583
    ADS1115_REG_FACTOR    = 0x7FFF

    ADS1115_BUSY          = 0x0000
    ADS1115_START_ISREADY = 0x8000

    ADS1115_COMP_INC = 0x1000

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


class ADS1X15(object):
    __autoRangeMode = False
    __voltageRange = 2048
    __measureMode = ADS1X15Constants.ADS1115_SINGLE
    
    def __init__(self, i2c: SoftI2C, address = ADS1X15Constants.ADS1115_DEFAULT_ADDR):
        self.__address = address
        self.__i2c = i2c
        try:
            self.reset()
        except OSError:  # I2C bus error:
            raise ValueError("Can't connect to the ADS1115. Check wiring, address, etc.")
        
        self.set_voltage_range_mv(ADS1X15Constants.ADS1115_RANGE_2048)
        self.__write_ads1115(ADS1X15Constants.ADS1115_LO_THRESH_REG, 0x8000)
        self.__write_ads1115(ADS1X15Constants.ADS1115_HI_THRESH_REG, 0x7FFF)
        self.__measureMode = ADS1X15Constants.ADS1115_SINGLE
        self.__autoRangeMode = False
        
    def set_alert_pin_mode(self, mode):
        reg = self.__get_conf_reg()
        reg &= ~0x8003
        reg |= mode
        self.__set_conf_reg(reg)

    def set_alert_latch(self, latch):
        reg = self.__get_conf_reg()
        reg &= ~0x8004
        reg |= latch
        self.__set_conf_reg(reg)
        
    def set_alert_pol(self, polarity):
        reg = self.__get_conf_reg()
        reg &= ~0x8008
        reg |= polarity
        self.__set_conf_reg(reg)

    def set_alert_mode_and_limit_v(self, mode, hi_thres, lo_thres):
        reg = self.__get_conf_reg()
        reg &= ~0x8010
        reg |= mode
        self.__set_conf_reg(reg)
        alert_limit = self.__calc_limit(hi_thres)
        self.__write_ads1115(ADS1X15Constants.ADS1115_HI_THRESH_REG, alert_limit)
        alert_limit = self.__calc_limit(lo_thres)
        self.__write_ads1115(ADS1X15Constants.ADS1115_LO_THRESH_REG, alert_limit)
        
    def __calc_limit(self, raw_limit):
        limit = int((raw_limit * ADS1X15Constants.ADS1115_REG_FACTOR / self.__voltageRange) * 1000)
        if limit > 32767:                       
            limit -= 65536
        return limit
        
    def reset(self):
        return self.__set_conf_reg(ADS1X15Constants.ADS1115_REG_RESET_VAL)
        
    def set_voltage_range_mv(self, new_range):
        current_voltage_range = self.__voltageRange
        current_conf_reg = self.__get_conf_reg()
        current_range = (current_conf_reg >> 9) & 7
        current_alert_pin_mode = current_conf_reg & 3
        
        self.set_measure_mode(ADS1X15Constants.ADS1115_SINGLE)
       
        if new_range == ADS1X15Constants.ADS1115_RANGE_6144:
            self.__voltageRange = 6144
        elif new_range == ADS1X15Constants.ADS1115_RANGE_4096:
             self.__voltageRange = 4096
        elif new_range == ADS1X15Constants.ADS1115_RANGE_2048:
            self.__voltageRange = 2048
        elif new_range == ADS1X15Constants.ADS1115_RANGE_1024:
            self.__voltageRange = 1024
        elif new_range == ADS1X15Constants.ADS1115_RANGE_0512:
            self.__voltageRange = 512
        elif new_range == ADS1X15Constants.ADS1115_RANGE_0256:
            self.__voltageRange = 256
 
        if (current_range != new_range) and (current_alert_pin_mode != ADS1X15Constants.ADS1115_DISABLE_ALERT):
            alert_limit = self.__read_ads1115(ADS1X15Constants.ADS1115_HI_THRESH_REG)
            alert_limit = alert_limit * (current_voltage_range / self.__voltageRange)
            self.__write_ads1115(ADS1X15Constants.ADS1115_HI_THRESH_REG, alert_limit)
            alert_limit = self.__read_ads1115(ADS1X15Constants.ADS1115_LO_THRESH_REG)
            alert_limit = alert_limit * (current_voltage_range / self.__voltageRange)
            self.__write_ads1115(ADS1X15Constants.ADS1115_LO_THRESH_REG, alert_limit)
     
        current_conf_reg &= ~0x8E00
        current_conf_reg |= new_range
        self.__set_conf_reg(current_conf_reg)
        rate = self.__get_conv_rate()
        self.__delay_acc_to_rate(rate)
        
    def set_auto_range(self):
        current_conf_reg = self.__get_conf_reg()
        self.set_voltage_range_mv(ADS1X15Constants.ADS1115_RANGE_6144)
        
        if self.__measureMode == ADS1X15Constants.ADS1115_SINGLE:
            self.set_measure_mode(ADS1X15Constants.ADS1115_CONTINUOUS)
            conv_rate = self.__get_conv_rate()
            self.__delay_acc_to_rate(conv_rate)
        
        raw_result = abs(self.__get_conv_reg())
        opt_range = ADS1X15Constants.ADS1115_RANGE_6144
        
        if raw_result < 1093:
            opt_range = ADS1X15Constants.ADS1115_RANGE_0256
        elif raw_result < 2185:
            opt_range = ADS1X15Constants.ADS1115_RANGE_0512
        elif raw_result < 4370:
            opt_range = ADS1X15Constants.ADS1115_RANGE_1024
        elif raw_result < 8738:
            opt_range = ADS1X15Constants.ADS1115_RANGE_2048
        elif raw_result < 17476:
            opt_range = ADS1X15Constants.ADS1115_RANGE_4096
            
        self.__set_conf_reg(current_conf_reg)
        self.set_voltage_range_mv(opt_range)
        
    def set_permanent_auto_range_mode(self, auto_mode):
        if auto_mode:
            self.__autoRangeMode = True
        else:
            self.__autoRangeMode = False
                   
    def set_measure_mode(self, m_mode):
        reg = self.__get_conf_reg()
        self.__measureMode = m_mode
        reg &= ~0x8100
        reg |= m_mode
        self.__set_conf_reg(reg)
        
    def set_compare_channels(self, comp_channels):
        reg = self.__get_conf_reg()
        reg &= ~0xF000
        reg |= comp_channels
        self.__set_conf_reg(reg)
        
        if not (reg & 0x0100):  # if not single shot mode
            conv_rate = self.__get_conv_rate()
            for i in range(2):
                self.__delay_acc_to_rate(conv_rate)
            
    def set_single_channel(self, channel):
        if channel >= 4:
            return
        self.set_compare_channels(ADS1X15Constants.ADS1115_COMP_0_GND + (ADS1X15Constants.ADS1115_COMP_INC * channel))
        
    def is_busy(self):
        reg = self.__get_conf_reg()
        return not((reg>>15) & 1)
    
    def start_single_measurement(self):
        reg = self.__get_conf_reg()
        reg |= (1 << 15)
        self.__set_conf_reg(reg)
        
    def get_result_v(self):
        return self.get_result_mv()/1000

    def get_result_mv(self):
        raw_result = self.get_raw_result()
        return raw_result * self.__voltageRange / ADS1X15Constants.ADS1115_REG_FACTOR

    def get_raw_result(self):
        raw_result = self.__get_conv_reg()
                
        if self.__autoRangeMode:
            if (abs(raw_result) > 26214) and (self.__voltageRange != 6144): # 80%
                self.set_auto_range()
                raw_result = self.__get_conv_reg()
            elif (abs(raw_result) < 9800) and (self.__voltageRange != 256):  # 30%
                self.set_auto_range()
                raw_result = self.__get_conv_reg()
                
        return raw_result
    
    def __get_conv_reg(self):
        raw_result = self.__read_ads1115(ADS1X15Constants.ADS1115_CONV_REG)
        if raw_result > 32767:
            raw_result -= 65536
        return raw_result
    
    def get_result_with_range(self, min_limit, max_limit):
        raw_result = self.get_raw_result()
        result = raw_result * (max_limit - min_limit) / 65536
        return result

    def get_result_with_range_and_max_volt(self, min_limit, max_limit, max_millivolt):
        result = self.get_result_with_range(min_limit, max_limit)
        result = result * self.__voltageRange / max_millivolt
        return result

    def get_voltage_range_mv(self):
        return self.__voltageRange

    def set_alert_pin_to_conversion_ready(self):
        self.__write_ads1115(ADS1X15Constants.ADS1115_LO_THRESH_REG, (0<<15))
        self.__write_ads1115(ADS1X15Constants.ADS1115_HI_THRESH_REG, (1<<15))

    def clear_alert(self):
        self.__read_ads1115(ADS1X15Constants.ADS1115_CONV_REG)
    
    def __set_conf_reg(self, reg_val):
        self.__write_ads1115(ADS1X15Constants.ADS1115_CONFIG_REG, reg_val)
    
    def __get_conf_reg(self):
        return self.__read_ads1115(ADS1X15Constants.ADS1115_CONFIG_REG)
        
    def __get_conv_rate(self):
        reg = self.__get_conf_reg()
        return reg & 0xE0
    
    def set_conv_rate(self, rate):
        reg = self.__get_conf_reg()
        reg &= ~0x80E0
        reg |= rate
        self.__set_conf_reg(reg)
    
    @staticmethod
    def __delay_acc_to_rate(rate):
        if rate == ADS1X15Constants.ADS1115_8_SPS:
            sleep_ms(130)
        elif rate == ADS1X15Constants.ADS1115_16_SPS:
            sleep_ms(65)
        elif rate == ADS1X15Constants.ADS1115_32_SPS:
            sleep_ms(32)
        elif rate == ADS1X15Constants.ADS1115_64_SPS:
            sleep_ms(16)
        elif rate == ADS1X15Constants.ADS1115_128_SPS:
            sleep_ms(8)
        elif rate == ADS1X15Constants.ADS1115_250_SPS:
            sleep_ms(4)
        elif rate == ADS1X15Constants.ADS1115_475_SPS:
            sleep_ms(3)
        elif rate == ADS1X15Constants.ADS1115_860_SPS:
            sleep_ms(2)
    
    def __write_ads1115(self, reg, val):
        self.__i2c.writeto_mem(self.__address, reg, self.__to_byte_array(val))
        
    def __read_ads1115(self, reg):
        reg_val = self.__i2c.readfrom_mem(self.__address, reg, 2)
        return self.__bytes_to_int(reg_val)
    
    @staticmethod
    def __to_byte_array(value: int):
#        return bytearray(intVal.to_bytes(2, 'big'))
        return struct.pack('>i', value)[2:]
    
    @staticmethod
    def __bytes_to_int(bytes_to_convert):
        return int.from_bytes(bytes_to_convert, 'big') # "big" = MSB at beginning

