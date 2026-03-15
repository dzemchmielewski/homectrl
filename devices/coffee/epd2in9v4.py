import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

from machine import SPI, Pin
from time import sleep_ms

logger = logging.getLogger(__name__)

class EPD2in9V4:
    """
    MicroPython driver for 2.9inch e-Paper Module (B) V4
    Supports 3-color display: Black, White, and Red/Yellow
    Resolution: 128x296
    """

    def __init__(self, width: int, height: int, spi: SPI, cs_pin: Pin, dc_pin: Pin, rst_pin: Pin, busy_pin: Pin, pwr_pin: Pin = None):
        self.debug = True
        self.spi = spi
        self.cs_pin, self.dc_pin, self.rst_pin, self.busy_pin = cs_pin, dc_pin, rst_pin, busy_pin
        self.pwr_pin = pwr_pin
        self.width, self.height = width, height

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
        sleep_ms(5)
        self.rst_pin.value(1)
        sleep_ms(200)
        self.wait_until_ready()
        logger.debug("Hardware reset done")

    def reset_sw(self):
        # Software Reset
        self.command(b'\x12')
        self.wait_until_ready()
        if self.debug:
            logger.debug("Software reset done")

    def isbusy(self):
        # For this display: 0: idle, 1: busy (opposite of epd7in5v2)
        return self.busy_pin.value() == 1

    def wait_until_ready(self, sleepms: int = None):
        if sleepms:
            sleep_ms(sleepms)
        self.send_command(0X71)
        if self.isbusy():
            logger.debug("Display busy, waiting...")
        while self.isbusy():
            sleep_ms(200)
        logger.debug("Display ready")

    def sleep(self):
        logger.debug("Putting display to sleep...")
        self.send_command(0x10)
        self.send_data(0x01)
        sleep_ms(2000)
        logger.debug("Display sleep done")

    def init(self):
        logger.debug("Initializing display...")

        # Power on if power pin is provided
        if self.pwr_pin:
            self.pwr_pin.on()
            sleep_ms(100)

        self.reset_hw()   # pulse RST pin to hardware-reset all registers to defaults
        self.reset_sw()   # send 0x12 SWRESET + wait — second full reset via SPI

        # ------------ Temperature sensor and LUT configuration ------------
        # Select the internal temperature sensor as the temperature source
        self.send_command(0x18)
        self.send_data(0x80)    # 0x80 = use built-in sensor (vs 0x48 = external)

        # Execute update sub-sequence: enable clock → read temp from sensor → load LUT → disable clock
        # This reads the actual die temperature and loads the corresponding waveform LUT
        self.send_command(0x22)
        self.send_data(0xB1)    # sequence flags: 0b10110001
        self.send_command(0x20) # activate the sequence
        self.wait_until_ready()

        # Override the temperature register with 90°C to force the fast-refresh LUT
        # Higher temperature → shorter waveform → faster refresh (at some quality cost)
        self.send_command(0x1A)
        self.send_data(0x5a)    # 0x5A = 90 (decimal), temperature in °C
        self.send_data(0x00)    # high byte (temperature fits in low byte)

        # Re-load the LUT now using the overridden 90°C temperature value
        # Sequence: enable clock → load LUT → disable clock
        self.send_command(0x22)
        self.send_data(0x91)    # sequence flags: 0b10010001
        self.send_command(0x20) # activate the sequence
        self.wait_until_ready()
        # ------------

        # Set gate driver count = display height − 1 (296 lines → 0x0127)
        # Without this the chip defaults to 303 gates (wrong for this panel)
        self.send_command(0x01)
        self.send_data((self.height-1)%256)   # low byte:  0x27
        self.send_data((self.height-1)//256)  # high byte: 0x01
        self.send_data(0x00)                  # gate scanning order: default

        # Data Entry Mode: X increments first, then Y (left-to-right, top-to-bottom)
        # 0x03 is the chip default but set explicitly for clarity
        self.send_command(0x11)
        self.send_data(0x03)

        # RAM X address window: byte 0 … byte (width/8 − 1), i.e. columns 0..15 for 128px
        self.send_command(0x44)
        self.send_data(0x00)
        self.send_data(self.width//8-1)

        # RAM Y address window: row 0 … row (height − 1), i.e. 0..295 for 296px
        self.send_command(0x45)
        self.send_data(0x00)                  # Y start low
        self.send_data(0x00)                  # Y start high
        self.send_data((self.height-1)%256)   # Y end low
        self.send_data((self.height-1)//256)  # Y end high

        # Border waveform: keep border white during refresh
        self.send_command(0x3C)
        self.send_data(0x05)

        # Display Update Control: normal black RAM, normal red RAM polarity
        self.send_command(0x21)
        self.send_data(0x00)
        self.send_data(0x80)

        # Route internal temperature sensor to LUT loader
        self.send_command(0x18)
        self.send_data(0x80)

        # Reset the RAM write cursor to (0, 0) so the first data byte lands at top-left
        self.send_command(0x4E)
        self.send_data(0x00)            # X counter = 0
        self.send_command(0x4F)
        self.send_data(0x00)            # Y counter low  = 0
        self.send_data(0x00)            # Y counter high = 0

        self.wait_until_ready()   # ensure all init commands are processed before first use
        logger.debug("Initialization done")

    def deinit(self, deinit_spi: bool = True):
        logger.debug("Deinitializing display...")
        if deinit_spi:
            self.spi.deinit()
        self.rst_pin.off()
        self.dc_pin.off()
        if self.pwr_pin:
            self.pwr_pin.off()
        logger.debug("Display deinited")

    def display(self, black_buffer: bytes = None, red_buffer: bytes = None):
        """
        Display image buffers on the e-paper screen.

        Args:
            black_buffer: Buffer for black/white image (None for all white)
            red_buffer: Buffer for red/yellow image (None for no red/yellow)
        """
        logger.debug("Sending display data...")

        # Send black/white image data
        if black_buffer is not None:
            logger.debug("Sending black buffer...")
            self.send_command(0x24)
            self.data(black_buffer)

        # Send red/yellow image data
        if red_buffer is not None:
            logger.debug("Sending red buffer...")
            self.send_command(0x26)
            # Invert red buffer data: 0x00 (red) becomes 0xFF, 0xFF (white) becomes 0x00
            self.data(bytes(0xFF - b for b in red_buffer))

        self.refresh()

    def clear(self):
        """Clear the display to all white."""
        logger.debug("Clearing display...")

        buffer_size = int(self.width * self.height / 8)

        # Clear black buffer
        self.send_command(0x24)
        for i in range(buffer_size):
            self.send_data(0xFF)

        # Clear red buffer
        self.send_command(0x26)
        for i in range(buffer_size):
            self.send_data(0x00)

        self.refresh()
        logger.debug("Display cleared")

    def refresh(self):
        logger.debug("Refreshing display...")
        self.send_command(0x22) #Display Update Control
        # self.send_data(0xF7)
        self.send_data(0xC7) # skip temp/LUT
        self.send_command(0x20) #Activate Display Update Sequence
        self.wait_until_ready()
        logger.debug("Display refresh done")


if __name__ == "__main__":
    # Example usage - adjust pins according to your hardware
    spi = SPI(1, baudrate=4_000_000, sck=Pin(4), mosi=Pin(16))
    cs = Pin(0, Pin.OUT)
    dc = Pin(2, Pin.OUT)
    rst = Pin(15, Pin.OUT)
    busy = Pin(13, Pin.IN)

    # Display dimensions
    #w, h = 296, 128
    w, h = 128, 296

    epd = EPD2in9V4(w, h, spi, cs, dc, rst, busy)
    try:
        epd.init()
        # epd.clear()

        from display_coffee import CoffeeDisplay
        import framebuf
        coffee = CoffeeDisplay(h, w, framebuf.MONO_HLSB)
        coffee.testscreen()

        epd.display(coffee.black.buffer, coffee.red.buffer)
        epd.sleep()
    finally:
        epd.deinit()