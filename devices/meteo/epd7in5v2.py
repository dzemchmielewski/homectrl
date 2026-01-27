import framebuf
import time
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

from machine import SPI, Pin, SoftSPI
from time import sleep_ms

from toolbox.framebufext import FrameBufferExtension

logger = logging.getLogger(__name__)

class EPD7in5V2:

    def __init__(self, width: int, height: int, spi: SPI, cs_pin: Pin, dc_pin: Pin, rst_pin: Pin, busy_pin: Pin, pwr_pin: Pin):
        self.debug = True
        self.spi = spi
        self.cs_pin, self.dc_pin, self.rst_pin, self.busy_pin, self.pwr_pin = cs_pin, dc_pin, rst_pin, busy_pin, pwr_pin
        self.width, self.height = width, height

        # Look-Up Tables for 4-gray display
        self._lut_v1 = None  # For command 0x10
        self._lut_v2 = None   # For command 0x13

        logger.debug(f"Display size: {self.width} x {self.height}")
        logger.debug(f"PINS: CS={self.cs_pin}, DC={self.dc_pin}, RST={self.rst_pin}, BUSY={self.busy_pin}, PWR={self.pwr_pin}")

    def command(self, command: bytes, data: bytes = None):
        self.dc_pin.value(0)
        self.cs_pin.value(0)
        self.spi.write(command)
        self.cs_pin.value(1)
        if data:
            self.data(data)

    def send_command(self, command: int):
        self.command(bytes([command]))

    def send_data(self, data: int):
        self.data(bytes([data]))

    def data(self, data: bytes):
        self.dc_pin.value(1)
        self.cs_pin.value(0)
        self.spi.write(data)
        self.cs_pin.value(1)

    def reset_hw(self):
        logger.debug("Performing hardware reset...")
        self.rst_pin.value(1)
        sleep_ms(200)
        self.rst_pin.value(0)
        sleep_ms(2)
        self.rst_pin.value(1)
        self.wait_until_ready(200)
        logger.debug("Hardware reset done")

    def isbusy(self):
        self.send_command(0x71)
        return self.busy_pin.value() == 0 # 0: busy, 1: idle
        # return self.busy_pin.value() == 1

    def wait_until_ready(self, sleepms: int = None):
        if sleepms:
            sleep_ms(sleepms)
        if self.isbusy():
            logger.debug("Display busy, waiting...")
        sleep_ms(50)
        while self.isbusy():
            sleep_ms(20)
        logger.debug("Display ready")
        sleep_ms(20)

    def sleep(self):
        logger.debug(f"Busy before sleep: {self.isbusy()}")
        logger.debug("Putting display to sleep...")
        self.command(b'\x02') # POWER_OFF
        self.data(b'\x00')
        logger.debug(f"Busy after power off command: {self.isbusy()}")
        sleep_ms(100)

        self.command(b'\x07') # DEEP_SLEEP
        self.data(b'\xA5')
        logger.debug(f"Busy after deep sleep command: {self.isbusy()}")

        sleep_ms(2000)
        logger.debug("Display sleep done")
        logger.debug(f"Busy after sleep: {self.isbusy()}")

    def init(self, mode: int):
        logger.debug(f"Initializing display... Mode: {mode}")
        self.pwr_pin.on()
        sleep_ms(100)
        self.reset_hw()

        if mode == framebuf.MONO_HLSB or mode == framebuf.MONO_HMSB:
            logger.debug("1bpp mode selected")
            self.send_command(0x06)  # btst
            self.data(b'\x17\x17\x28\x17')

            self.send_command(0x01)  # POWER SETTING
            self.data(b'\x07\x07\x28\x17')

            self.send_command(0x04)  # POWER ON
            self.wait_until_ready(100)

            self.send_command(0X00)			#PANNEL SETTING
            self.send_data(0x1F)   #KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f
            self.send_command(0x61)        	#tres
            self.data(b'\x03\x20\x01\xE0')		#source 800

            self.send_command(0X15)
            self.send_data(0x00)

            # If the screen appears gray, use the annotated initialization command
            self.send_command(0X50)
            self.data(b'\x10\x07')

            self.send_command(0X60)			#TCON SETTING
            self.send_data(0x22)
            self.wait_until_ready()

        elif mode == framebuf.GS2_HMSB:
            logger.debug("2bpp mode selected")
            self._init_lut()
            self.send_command(0X00)			#PANNEL SETTING
            self.send_data(0x1F)   #KW-3f   KWR-2F	BWROTP 0f	BWOTP 1f

            self.send_command(0X50)
            self.data(b'\x10\x07')

            self.send_command(0x04) #POWER ON
            self.wait_until_ready(100)

            #Enhanced display drive(Add 0x06 command)
            self.send_command(0x06)			#Booster Soft Start
            self.data (b'\x27\x27\x18\x17')

            self.send_command(0xE0)
            self.send_data(0x02)
            self.send_command(0xE5)
            self.send_data(0x5F)
        else:
            raise ValueError(f"Unsupported framebuffer mode: {mode}")

        logger.debug("Initialization done")

    def _init_lut(self):
        """Pre-calculates bit transformations for 4-Gray logic."""
        self._lut_v1 = bytearray(256) # For command 0x10
        self._lut_v2 = bytearray(256) # For command 0x13
        for i in range(256):
            # Each input byte contains 4 pixels (2 bits each)
            # We transform them into 4 output bits (1 bit each)
            out_v1, out_v2 = 0, 0

            # Process the 4 pixels in the byte from MSB to LSB
            # for shift in (6, 4, 2, 0):
            # or leave it as is:
            for shift in (0, 2, 4, 6):
                val = (i >> shift) & 0x03 # Extract 2-bit pixel

                # Logic for Command 0x10 (Pass 1)
                # 00(Blk)->1, 01(DkG)->0, 10(LtG)->1, 11(Wht)->0
                # "Even numbers are 1"
                bit_v1 = 1 if (val % 2 == 0) else 0

                # Logic for Command 0x13 (Pass 2)
                # 00(Blk)->1, 01(DkG)->1, 10(LtG)->0, 11(Wht)->0
                # "Values less than 2 are 1"
                bit_v2 = 1 if (val < 2) else 0

                # Shift into position
                out_v1 = (out_v1 << 1) | bit_v1
                out_v2 = (out_v2 << 1) | bit_v2

            self._lut_v1[i] = out_v1
            self._lut_v2[i] = out_v2

    def _send_plane(self, image, lut):
        """
        Helper to process and send a single color plane.

        Args:
            image (bytearray/list): The source image data.
            lut (bytearray): The look-up table to apply for this plane.
        """
        # Batch size: 128 output bytes (derived from 256 input bytes).
        CHUNK_SIZE = 256
        total_len = len(image)

        for i in range(0, total_len, CHUNK_SIZE):
            chunk_end = min(i + CHUNK_SIZE, total_len)

            # Allocate small temporary buffer for this batch
            # Size is half the chunk size because 2 input bytes = 1 output byte
            out_buf = bytearray((chunk_end - i) // 2)

            idx = 0
            # Process pairs of bytes
            for k in range(i, chunk_end, 2):
                # Combine two input bytes using the LUT
                # High nibble from first byte, Low nibble from second byte
                high_nibble = lut[image[k]] << 4
                low_nibble = lut[image[k+1]]
                # Swap k and k+1 if the image still looks "jittery" horizontally
                out_buf[idx] = high_nibble | low_nibble
                idx += 1

            # Send the optimized batch
            self.data(out_buf)

    def deinit(self, deinit_spi: bool = True):
        logger.debug("Deinitializing display...")
        if deinit_spi:
            self.spi.deinit()
        self.rst_pin.off()
        self.dc_pin.off()
        self.pwr_pin.off()
        logger.debug("Display deinited")

    def display(self, fb: FrameBufferExtension):
        logger.debug(f"Framebuffer mode: {fb.mode}, size: {fb.width} x {fb.height}")
        logger.debug(f"Display mode: {self.width} x {self.height}")

        buf, w, h = fb.buffer, fb.width, fb.height

        if fb.mode == framebuf.MONO_HLSB or fb.mode == framebuf.MONO_HMSB:
            logger.debug("1bpp display")
            # OLD buffer - invert bits
            # but, we do not inverting, because frambuf <-> display mapping is already inverted
            self.command(b'\x10')
            self.data(buf)

            # Back to normal buffer
            # i.e. invert for display
            for i in range(len(buf)):
                buf[i] = ~buf[i] & 0xFF
            self.command(b'\x13')
            self.data(buf)

            self.command(b'\x12')
            # self.data(b'\x00')  # removed entirely, as command 0x12 usually takes no data.
            self.wait_until_ready()

        elif fb.mode == framebuf.GS2_HMSB:
            # Pass 1: Light/White component (Command 0x10)
            logger.debug("pass 1 - Light/White component...")
            self.send_command(0x10)
            self._send_plane(buf, self._lut_v1)
            logger.debug("pass 1 - Light/White component DONE")

            # Pass 2: Dark/Black component (Command 0x13)
            logger.debug("pass 2 - Dark/Black component...")
            self.send_command(0x13)
            self._send_plane(buf, self._lut_v2)
            logger.debug("pass 2 - Dark/Black component DONE")

            # Refresh command sequence
            self.send_command(0x12) # Refresh
            logger.debug("Refresh command sent, waiting for display to be ready...")
            self.wait_until_ready(100)

        else:
            raise ValueError(f"Unsupported framebuffer mode: {fb.mode}")

        self.sleep()

if __name__ == "__main__":
    import gc
    gc.collect()
    print(f"Memory before display test: {gc.mem_free()} bytes free")


    #dev:
    # spi = SoftSPI(sck=Pin(7), mosi=Pin(6), miso=Pin(0))
    spi = SPI(1, baudrate=4_000_000, sck=Pin(5), mosi=Pin(4))
    cs = Pin(6, Pin.OUT)
    dc = Pin(7, Pin.OUT)
    rst = Pin(0, Pin.OUT)
    busy = Pin(1, Pin.IN, Pin.PULL_UP)
    pwr = Pin(8, Pin.OUT)

    # blue LED - 11
    # yellow - 20
    # 21 - pull it down. When 1 - do not sleep

    from display_meteo import MeteoDisplay
    import json

    data = {
        'astro': json.loads(open("astro.json").read()),
        'meteo': json.loads(open("meteo.json").read()),
        'precipitation': json.loads(open("precipitation.json").read()),
        'temperature': json.loads(open("temperature.json").read()),
        'meteofcst': json.loads(open("meteofcst.json").read())['meteofcst'],
        'holidays': json.loads(open("holidays.json").read()),
        'battery': time.localtime()[4],
    }
    # Mangling data:
    from_day_offset = -1
    to_day_offset = 4

    # Astro:
    # Pick only 5 days of astro data:
    data['astro']['astro'] = [astro_data for astro_data in data['astro']['astro'] if astro_data['day']['day_offset'] in range(from_day_offset, to_day_offset)]

    print(f"Memory before display init: {gc.mem_free()} bytes free")

    w, h = 800, 480
    gc.collect()
    gc.threshold(gc.mem_free() // 4)

    meteo = MeteoDisplay(w, h, framebuf.GS2_HMSB)
    meteo.update(data)
    fb = meteo.fb

    # fb = FrameBufferExtension(w, h, framebuf.GS2_HMSB)
    # with open('morderczka-2bits.gray', 'rb') as f:
    #     f.readinto(fb.buffer)

    epd = EPD7in5V2(w, h, spi, cs, dc, rst, busy, pwr)
    try:
        epd.init(fb.mode)
        epd.display(fb)
    finally:
        epd.deinit()






