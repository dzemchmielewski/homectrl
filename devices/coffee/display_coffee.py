import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import framebuf
from toolbox.framebufext import FrameBufferExtension, FM
from toolbox.fbtransform import rotate

class Colors:
    BLACK, WHITE = 0, 1
    @property
    def foreground(self):
        return self.BLACK
    @property
    def background(self):
        return self.WHITE
    def __init__(self):
        self.map = {
            'text': self.foreground,
            'background': self.background,
            'foreground': self.foreground,
        }
        self.palette = FrameBufferExtension.palette([self.foreground, self.background], framebuf.MONO_HLSB)

class CoffeeDisplay:

    READY = 1
    ALERT = 2
    BUSY = 3

    def __init__(self, width: int, height: int, fb_mode: int = framebuf.MONO_HLSB):

        self.black = FrameBufferExtension(width, height, fb_mode)
        self.red = FrameBufferExtension(width, height, fb_mode)
        self.colors = Colors()

        if self.colors.background == 1:
            # self.palette = framebuf.FrameBuffer(bytearray(2), 1, 2, framebuf.MONO_HLSB)  # 2 entries × 1 byte each
            self.palette = FrameBufferExtension.palette([1, 0], framebuf.MONO_HLSB)
            FM.palette = FrameBufferExtension.palette([1, 0], framebuf.MONO_HLSB)
            # self.palette.pixel(0, 0, 1)  # 0 → 1
            # self.palette.pixel(0, 1, 0)  # 1 → 0
        else:
            # Identity palette: 0 → 0 and 1 → 1 is default, so no need to create one.
            # Also, creating an identity palette seems  not to work correctly.
            self.palette = None
            FM.palette = FrameBufferExtension.palette([0, 1], framebuf.MONO_HLSB)

        # set default font, so we don't have to specify it for each font:
        FM.liberation.sans.bold.normal.directory = "fonts"

    def update(self, data: dict):
        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

        fb = self.black
        fb.rect(10, 10, 60, 60, self.colors.foreground, True)
        fb.line(0, 0, fb.width - 1, fb.height - 1, self.colors.foreground)
        fb.line(0, fb.height - 1, fb.width - 1, 0, self.colors.foreground)
        fb.textf("Ala ma kota!", 190, 70, font=FM.get.font(16), key=self.colors.background)

        # Red cross lines - vertical and horizontal
        fb = self.red
        fb.rect(35, 35, 60, 60, self.colors.foreground, True)
        fb.line(fb.width // 2, 0, fb.width // 2, fb.height - 1, self.colors.foreground)  # vertical
        fb.line(0, fb.height // 2, fb.width - 1, fb.height // 2, self.colors.foreground)  # horizontal
        fb.textf("Alice has a pussy!", 170, 100, font=FM.get.font(16), key=self.colors.background)

        # Remove black pixels where red pixels are ON
        for y in range(self.black.height):
            for x in range(self.black.width):
                if self.red.pixel(x, y) == self.colors.foreground and self.black.pixel(x, y) == self.colors.foreground:
                    self.black.pixel(x, y, self.colors.background)

        self.black = self.black.invert()
        self.black = self.rotate(self.black)
        self.red = self.rotate(self.red)

    def testscreen(self):
        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

        fb = self.black
        fb.rect(10, 10, 60, 60, self.colors.foreground, True)
        fb.line(0, 0, fb.width - 1, fb.height - 1, self.colors.foreground)
        fb.line(0, fb.height - 1, fb.width - 1, 0, self.colors.foreground)
        fb.textf("Ala ma kota!", 190, 70, font=FM.get.font(16), key=self.colors.background)

        # Red cross lines - vertical and horizontal
        fb = self.red
        fb.rect(35, 35, 60, 60, self.colors.foreground, True)
        fb.line(fb.width // 2, 0, fb.width // 2, fb.height - 1, self.colors.foreground)  # vertical
        fb.line(0, fb.height // 2, fb.width - 1, fb.height // 2, self.colors.foreground)  # horizontal
        fb.textf("Alice has a pussy!", 170, 100, font=FM.get.font(16), key=self.colors.background)

        # Remove black pixels where red pixels are ON
        for y in range(self.black.height):
            for x in range(self.black.width):
                if self.red.pixel(x, y) == self.colors.foreground and self.black.pixel(x, y) == self.colors.foreground:
                    self.black.pixel(x, y, self.colors.background)

        self.black = self.black.invert()
        self.black = self.rotate(self.black)
        self.red = self.rotate(self.red)

    @staticmethod
    def rotate(src: FrameBufferExtension):
        return rotate(270, src, FrameBufferExtension(src.height, src.width, src.mode))

    def clear(self):
        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

if __name__ == "__main__":
    coffee = CoffeeDisplay(296, 128, framebuf.MONO_HLSB)
    coffee.update({'battery': 50, 'level': 20, 'state': CoffeeDisplay.BUSY})
    from pgmexporter import PGMExporter
    PGMExporter('/tmp/output_black.pgm').export_fbext(coffee.black)
    PGMExporter('/tmp/output_red.pgm').export_fbext(coffee.red)

    # rotate back for testing, because the coffee display is in landscape orientation, but the
    # framebuffers are created in portrait orientation for easier drawing.:
    coffee.black = rotate(90, coffee.black, FrameBufferExtension(coffee.black.height, coffee.black.width, coffee.black.mode))
    coffee.red = rotate(90, coffee.red, FrameBufferExtension(coffee.red.height, coffee.red.width, coffee.red.mode))

    fb = FrameBufferExtension(coffee.black.width, coffee.black.height, framebuf.GS2_HMSB)
    if coffee.colors.background == coffee.colors.WHITE:
        fb.blit(coffee.black, 0, 0, 1, FrameBufferExtension.palette([0, 3, 0, 0], framebuf.GS2_HMSB))
        fb.blit(coffee.red, 0, 0, 3, FrameBufferExtension.palette([2, 3, 0, 0], framebuf.GS2_HMSB))
    else:
        fb.blit(coffee.black, 0, 0, 0, FrameBufferExtension.palette([0, 3, 0, 0], framebuf.GS2_HMSB))
        fb.blit(coffee.red, 0, 0, 2, FrameBufferExtension.palette([2, 1, 0, 0], framebuf.GS2_HMSB))

    logger.info("USED FONTS:")
    for font_file, font in FM.cache.items():
        logger.info(f" - {font_file} ({font}")

    PGMExporter('/tmp/output.pgm').export_fbext(fb)
