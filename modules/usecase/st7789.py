from machine import SPI, Pin

import st7789
import vga2_bold_16x32 as font

#LCD:
# 4  CS
# 5  RESET
# 6  D/C
# 46 SDI (MOSI)
# 17 SCK
# 18 LED
# 8 SDO (MISO)

# CTP:
# 7  CLK/SCL
# 15 CS/RST
# 16 DIN/SDA
# 3 OUT
# 9 IRQ/INT

display = st7789.ST7789(
    SPI(2, baudrate=40000000, sck=Pin(17), mosi=Pin(46), miso=Pin(8)),
    240,
    320,
    reset=Pin(5, Pin.OUT),
    cs=Pin(4, Pin.OUT),
    dc=Pin(6, Pin.OUT),
    backlight=Pin(18, Pin.OUT),
    rotation=0)

display.fill(st7789.RED)

def center(text):
    length = len(text)
    display.text(font, text,
        display.width // 2 - length // 2 * font.WIDTH,
        display.height // 2 - font.HEIGHT //2,
        st7789.WHITE, st7789.RED)

center('Dupa!')

