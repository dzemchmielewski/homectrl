import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import framebuf  # type: ignore[import-not-found]
from toolbox import fbtransform
from toolbox.framebufext import FrameBufferExtension, FM, FrameBufferOffset, FrameBufferFont
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

class CoffeeView:

    def __init__(self, width: int, height: int, fb_mode: int = framebuf.MONO_HLSB):

        self.black = FrameBufferExtension(width, height, fb_mode)
        self.red = FrameBufferExtension(width, height, fb_mode)
        self.black_out = FrameBufferExtension(height, width, fb_mode)
        self.red_out   = FrameBufferExtension(height, width, fb_mode)
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
        FM.family('URWBookman').regular.classification('').directory = "fonts"

    def red_frame(self, black, red, text, font, pad_top = 0, pad_bottom = 0):
        pad = 6
        thick, radius = 5, 10
        frame = red.rectround(pad, pad_top, red.width - (2*pad), red.height - pad_top - pad_bottom, self.colors.foreground, radius, True)
        frame.rectround(thick, thick, frame.width - (2*thick), frame.height - (2*thick), self.colors.background, radius, True)
        bl = FrameBufferOffset(black.fb, frame.x, frame.y, frame.width, frame.height)
        bl.rectround(thick, thick, frame.width - (2*thick), frame.height - (2*thick), self.colors.foreground, radius, True)
        frame.textfalign(text, font, key=self.colors.background, x_spacing=5, top_margin=3)

    def render(self, data: dict):
        width, height, half_height = self.black.width, self.black.height, self.black.height // 2
        battery_height = 16

        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

        view_count = 0
        if data['coffee'] and data['coffee']['value'] is not None:
            view_count += 1
            font = FM.font(80)
        if data['message'] and data['message']['value'] is not None:
            view_count += 1
            font = FM.font(35)

        view_height = (height - battery_height) // view_count
        views = []
        for i in range(view_count):
            views.append((
                FrameBufferOffset(self.black, 0, (i * view_height) + battery_height, width, view_height),
                FrameBufferOffset(self.red, 0, (i * view_height)  + battery_height, width, view_height)))

        # Battery:
        battery = FrameBufferOffset(self.red if data['battery']['alert'] else self.black, 0,0, width, battery_height)
        image = FrameBufferExtension.fromfile("battery.fb")
        battery.blit(image, 4, 1, self.colors.background)
        level = FrameBufferOffset(self.red if data['battery']['alert'] else self.black, image.width + 8 , battery.y, battery.width -  image.width - 6, battery.height)
        w, h = level.width // 12, level.height
        for i in range(12):
            level.rect(1 + (i * w), 2, w - 2, h - 3, self.colors.foreground, i < data['battery']['value'])

        i = 0
        # Coffee:
        if data['coffee'] and data['coffee']['value'] is not None:
            text = f"{data['coffee']['value']}%"
            if data['coffee']['alert']:
                self.red_frame(views[i][0], views[i][1], text, font, pad_top=(6 if i == 0 else 3), pad_bottom=(6 if i == view_count - 1 else 3))
            else:
                views[i][0].textfalign(text, font,key=self.colors.background, x_spacing=5, top_margin=10)
            i += 1

        # Message:
        if data['message'] and data['message']['value'] is not None:
            if data['message']['alert']:
                self.red_frame(views[i][0], views[i][1], data['message']['value'], font, pad_top=(6 if i == 0 else 3), pad_bottom=(6 if i == view_count - 1 else 3))
            else:
                views[i][0].textfalign(data['message']['value'], font,key=self.colors.background, top_margin=10, x_spacing=5)
            i += 1

        #TEMP:
        self.black.rect(0, 0, width , height, self.colors.foreground)

        # # Remove black pixels where red pixels are ON
        # for y in range(self.black.height):
        #     for x in range(self.black.width):
        #         if self.red.pixel(x, y) == self.colors.foreground and self.black.pixel(x, y) == self.colors.foreground:
        #             self.black.pixel(x, y, self.colors.background)

        # Remove black pixels where red pixels are ON
        black_buf, red_buf = self.black.buffer, self.red.buffer
        for i in range(len(black_buf)):
            black_buf[i] |= (~red_buf[i]) & 0xFF

        self.rotate(self.black.invert(), self.black_out)
        self.rotate(self.red, self.red_out)

    def testscreen(self):
        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

        fb = self.black
        fb.rect(10, 10, 60, 60, self.colors.foreground, True)
        fb.line(0, 0, fb.width - 1, fb.height - 1, self.colors.foreground)
        fb.line(0, fb.height - 1, fb.width - 1, 0, self.colors.foreground)
        fb.textf("Ala ma kota!!!", 100, 70, font=FM.get.font(18), key=self.colors.background)

        # Red cross lines - vertical and horizontal
        fb = self.red
        fb.rect(35, 35, 60, 60, self.colors.foreground, True)
        fb.line(fb.width // 2, 0, fb.width // 2, fb.height - 1, self.colors.foreground)  # vertical
        fb.line(0, fb.height // 2, fb.width - 1, fb.height // 2, self.colors.foreground)  # horizontal
        fb.textf("Alice has a pussy!", 170, 100, font=FM.get.font(18), key=self.colors.background)

        # Remove black pixels where red pixels are ON
        # for y in range(self.black.height):
        #     for x in range(self.black.width):
        #         if self.red.pixel(x, y) == self.colors.foreground and self.black.pixel(x, y) == self.colors.foreground:
        #             self.black.pixel(x, y, self.colors.background)

        # Remove black pixels where red pixels are ON
        black_buf, red_buf = self.black.buffer, self.red.buffer
        for i in range(len(black_buf)):
            black_buf[i] |= (~red_buf[i]) & 0xFF

        self.rotate(self.black.invert(), self.black_out)
        self.rotate(self.red, self.red_out)

    @staticmethod
    def rotate(src: FrameBufferExtension, dst: FrameBufferExtension = None):
        if dst is None:
            dst = FrameBufferExtension(src.height, src.width, src.mode)
        return rotate(270, src, dst)

    def clear(self):
        self.black.fill(self.colors.background)
        self.red.fill(self.colors.background)

if __name__ == "__main__":
    import random
    messages = [None, "zmełłem", "kafke mielu"]
    data = {
        'battery': {
            'value': 21,#random.randint(0, 12),
            'alert': True if random.randint(0, 1) == 1 else False,
        },
        'coffee': {
            'value': random.randint(1,100),
            'alert': True if random.randint(0, 1) == 1 else False,
        },
        'message': {
            'value': messages[2], #messages[random.randint(0, len(messages) - 1)],
            'alert': True if random.randint(0, 1) == 1 else False,
        },
    }
    logger.info(data)

    coffee = CoffeeView(296, 128, framebuf.MONO_HLSB)
    coffee.render(data)
    #coffee.testscreen()

    from pgmexporter import PGMExporter
    PGMExporter('/tmp/output_black.pgm').export_fbext(coffee.black_out)
    PGMExporter('/tmp/output_red.pgm').export_fbext(coffee.red_out)

    fb = FrameBufferExtension(coffee.black_out.width, coffee.black_out.height, framebuf.GS2_HMSB)
    if coffee.colors.background == coffee.colors.WHITE:
        fb.blit(coffee.black_out, 0, 0, 1, FrameBufferExtension.palette([0, 3, 0, 0], framebuf.GS2_HMSB))
        fb.blit(coffee.red_out, 0, 0, 3, FrameBufferExtension.palette([2, 3, 0, 0], framebuf.GS2_HMSB))
    else:
        fb.blit(coffee.black_out, 0, 0, 0, FrameBufferExtension.palette([0, 3, 0, 0], framebuf.GS2_HMSB))
        fb.blit(coffee.red_out, 0, 0, 2, FrameBufferExtension.palette([2, 1, 0, 0], framebuf.GS2_HMSB))

    logger.info("USED FONTS:")
    for font_file, font in FM.cache.items():
        logger.info(f" - {font_file} ({font}")

    result = FrameBufferExtension(296, 128, framebuf.GS2_HMSB)
    fbtransform.rotate(90, fb, result)

    PGMExporter('/tmp/output.pgm').export_fbext(result)
