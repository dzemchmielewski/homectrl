import array

import logging
import struct
import framebuf

log = logging.getLogger(__name__)

class _FrameBufferExtension(framebuf.FrameBuffer):
    def __init__(self, width: int, height: int, mode, buffer = None):
        self.width, self.height, self.mode = width, height, mode
        if mode == framebuf.MONO_HLSB or mode == framebuf.MONO_VLSB:
            size = self.width * self.height // 8
        elif mode == framebuf.GS2_HMSB:
            size = self.width * self.height  // 4
        elif mode == framebuf.GS4_HMSB:
            size = self.width * self.height  // 2
        else:
            raise ValueError("Unsupported framebuf mode")

        if buffer and len(buffer) != size:
            raise ValueError("Buffer size does not match")

        self.buffer = buffer if buffer else memoryview(bytearray(size))
        log.debug("framebuf size: %d, %d, number of bytes: %d", self.width, self.height, size)
        super().__init__(self.buffer, self.width, self.height, self.mode)

    def deinit(self):
        if self.buffer:
            self.buffer.release()
        self.buffer = None

    def __del__(self):
        self.deinit()

class FrameBufferFont:

    def __init__(self,filename,cache_index = True, cache_chars = True, palette: _FrameBufferExtension = None):
        (self.stream, self.height,
        self.baseline, self.max_width,
        self.monospaced, self.index_len
        )  = self.open_mfnt_file(filename)

        self.cache_chars = cache_chars
        self.cache_index = cache_index or cache_chars
        self.index = None
        self.cache = {}
        self.palette = palette

    @staticmethod
    def open_mfnt_file(filename: str):
        stream = open(filename,"rb")
        header_data = stream.read(12)
        if len(header_data) != 12:
            raise ValueError("Corrupted header for MFNT font file")

        magic, height, baseline, max_width, monospaced, index_len = \
            struct.unpack("<4sBBBBL",header_data)
        if magic != b'MFNT':
            raise ValueError(f"{filename} is not a MicroFont file")

        log.debug(f"Loaded MicroFont '{filename}': height={height}, baseline={baseline}, max_width={max_width}, monospaced={monospaced}, index_len={index_len}")
        return stream, height, baseline, max_width, True if monospaced else False, index_len

    @staticmethod
    def read_int_16(l):
        return l[0] | (l[1] << 8)

    # Binary search of the sparse index.
    @staticmethod
    def bs(index, val):
        while True:
            m = (len(index) & ~ 7) >> 1
            v = index[m] | index[m+1] << 8
            if v == val:
                return index[m+2] | index[m+3] << 8
            if not m:
                return 0
            index = index[m:] if v < val else index[:m]

    # Return the character bitmap (horizontally mapped, and horizontally
    # padded to whole bytes), the height and width in pixels.
    def get_char(self, char):
        if self.cache_chars and char in self.cache:
            return self.cache[char]

        if char == ' ':
            result = self.get_char('.')
            _, char_height, char_width = result
            return None, char_height, char_width

        # Read the index in memory, if not cached.
        if self.index is not None:
            index = self.index
        else:
            self.stream.seek(0)
            index = self.stream.read(self.index_len)
            if self.cache_index:
                self.index = index

        # Get the character data offset inside the file
        # relative to the start of the data section, so the
        # real offset from the start is hdr_len + index_len + doff.
        doff = self.bs(memoryview(index), ord(char)) << 3

        # Access the char data inside the file and return it.
        self.stream.seek(12+self.index_len+doff) # 12 is header len.
        width = self.read_int_16(self.stream.read(2))
        char_data_len = (width + 7)//8 * self.height

        char_data = bytearray(char_data_len)
        self.stream.readinto(char_data)

        retval = framebuf.FrameBuffer(char_data, width, self.height, framebuf.MONO_HLSB), self.height, width
        if self.cache_chars:
            self.cache[char] = retval
        return retval

    def size(self, text: str, x_spacing: int = 0, y_spacing: int = 0):
        off_x, off_y = 0, 0
        for char in text:
            if char == '\n':
                off_x, off_y = 0, off_y + self.height + y_spacing
            else:
                _, _, char_width = self.get_char(char)
                off_x += x_spacing + char_width
        return off_x, off_y + self.height

    def deinit(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.cache:
            self.cache.clear()

    def __del__(self):
        self.deinit()

class FrameBufferExtension(_FrameBufferExtension):

    def __init__(self, width: int, height: int, mode, buffer = None):
        super().__init__(width, height, mode, buffer)

    @classmethod
    def fromfile(cls, file):
        with open(file, "rb") as f:
            buf = bytearray(f.read())
            w, h, format, _, data = buf[0], buf[1], buf[2], buf[3], buf[4:]
            log.debug(f"Reading framebuf from file {file}: width: {w}, height: {h}, format: {format}, buf len: {len(data)}")
            return FrameBufferExtension(w, h, format, data)

    @staticmethod
    def palette(colors: list, mode: int):
        # index 0 - background, index 1 - foreground, others - shades
        result = FrameBufferExtension(len(colors), 1, mode)
        for i, c in enumerate(colors):
            result.pixel(i, 0, c)
        return result

    def textf(self, text, x, y, font: FrameBufferFont, key: int = -1,
                  y_spacing: int = 0, x_spacing: int = 0, palette: FrameBufferExtension = None):
        off_x, off_y = 0, 0
        palette = palette if palette else font.palette
        for idx, char in enumerate(text):
            if char == '\n':
                off_x, off_y = 0, off_y + font.height + y_spacing
            elif char == "°":
                # degree symbol
                _, char_height, char_width = font.get_char('I')
                size =  (char_width - 1) //2
                int_size = int(size * (6/10))
                y_deg = y + off_y +  round(char_height * (2/10))
                # self.pixel(x + off_x, y_deg, palette.pixel(1, 0) if palette else key)
                self.ellipse(x + off_x + size, y_deg, size, size, palette.pixel(1, 0), True)
                self.ellipse(x+ off_x + size, y_deg, int_size, int_size, palette.pixel(0, 0), True)
                off_x += x_spacing + char_width

            else:
                glyph, char_height, char_width = font.get_char(char)
                if glyph is not None:
                    self.blit(glyph, x + off_x, y + off_y, key, palette)
                else:
                    self.rect(x + off_x, y + off_y, char_width, char_height, palette.pixel(0, 0) if palette else key, True)
                if x_spacing > 0 and idx < len(text) - 1:
                    self.rect(x + off_x + char_width, y + off_y, char_width, char_height, palette.pixel(0, 0) if palette else key, True)
                off_x += x_spacing + char_width
        return x + off_x, y + off_y + font.height

    @staticmethod
    def textposition(text, width, height, font: FrameBufferFont,
                     align_horiz='center', align_vert='center',
                     left_margin=0, top_margin=0, right_margin=0, bottom_margin=0,
                     **kwargs):
        size_x, size_y = font.size(text, kwargs.get('x_spacing', 0), kwargs.get('y_spacing', 0))

        if align_horiz == 'left':
            x = left_margin
        elif align_horiz == 'center':
            x = ((width - size_x) // 2) + (left_margin - right_margin) // 2
        elif align_horiz == 'right':
            x = width - size_x - right_margin
        else:
            raise ValueError(f"Invalid horizontal alignment: {align_horiz}. Possible values are 'left', 'center', 'right'.")

        if align_vert == 'top':
            y = top_margin
        elif align_vert == 'center':
            y = (height - size_y) // 2 + (top_margin - bottom_margin) // 2
        elif align_vert == 'bottom':
            y = height - size_y - bottom_margin
        else:
            raise ValueError(f"Invalid vertical alignment: {align_vert}. Possible values are 'top', 'center', 'bottom'.")

        return x, y

    def textfalign(self, text, font: FrameBufferFont,
                   align_horiz='center', align_vert='center',
                   left_margin=0, top_margin=0, right_margin=0, bottom_margin=0,
                   **kwargs):
        x, y = self.textposition(text,
                                 self.width, self.height, font,
                                 align_horiz, align_vert,
                                 left_margin=left_margin, top_margin=top_margin, right_margin=right_margin, bottom_margin=bottom_margin,
                                 **kwargs)
        return self.textf(text, x, y, font, **kwargs)

    def triangle(self, x1, y1, x2, y2, x3, y3, color, f=False):
        if f:
            # Simple filled triangle using polygon fill (if available)
            #self.poly(x1, y1, array.array('I', [ x1, y1, x2, y2, x3, y3]), color, True)
            # Simple scanline fill for triangle
            points = sorted([(x1, y1), (x2, y2), (x3, y3)], key=lambda p: p[1])
            x1, y1 = points[0]
            x2, y2 = points[1]
            x3, y3 = points[2]
            def interp(xa, ya, xb, yb, y):
                if ya == yb:
                    return xa
                return int(xa + (xb - xa) * (y - ya) / (yb - ya))
            for y in range(y1, y3 + 1):
                if y < y2:
                    xa = interp(x1, y1, x2, y2, y)
                    xb = interp(x1, y1, x3, y3, y)
                else:
                    xa = interp(x2, y2, x3, y3, y)
                    xb = interp(x1, y1, x3, y3, y)
                self.hline(min(xa, xb), y, abs(xa - xb) + 1, color)
        else:
            # Draw triangle outline
            self.line(x1, y1, x2, y2, color)
            self.line(x2, y2, x3, y3, color)
            self.line(x3, y3, x1, y1, color)

    def invert(self) -> "FrameBufferExtension":
        result = FrameBufferExtension(self.width, self.height, self.mode)
        for y in range(self.height):
            for x in range(self.width):
                result.pixel(x, y, (self.width - 1) - self.pixel(x, y))
        return result

    def convert(self, dst_mode: int, palette: "FrameBufferExtension") -> "FrameBufferExtension":
        if self.mode == framebuf.GS2_HMSB and (dst_mode == framebuf.MONO_HLSB or dst_mode == framebuf.MONO_HMSB):
            w, h = self.width, self.height
            result = FrameBufferExtension(w, h, dst_mode)
            dst_buf = result.buffer

            src_row_bytes = (w + 3) // 4  # 2bpp: 4 pixels per byte
            dst_row_bytes = (w + 7) // 8  # 1bpp: 8 pixels per byte

            for y in range(h):
                for x in range(w):
                    # Extract 2-bit pixel from source
                    src_byte = self.buffer[y * src_row_bytes + (x // 4)]

                    # NOTE: Although the mode is named GS2_HMSB, MicroPython's framebuf
                    # stores 2-bit pixels LSB-first inside each byte (pixel 0 in bits 1–0).
                    # Using the "theoretical" HMSB layout:
                    #     (3 - (x % 4)) * 2
                    # produces a mirrored image. The expression below matches the actual
                    # in-memory layout used by framebuf.

                    shift = (x % 4) * 2
                    gs = (src_byte >> shift) & 0x03

                    # Get 1-bit value from palette
                    bit = palette.pixel(gs, 0)

                    if bit:
                        dst_index = y * dst_row_bytes + (x // 8)
                        if dst_mode == framebuf.MONO_HMSB:
                            # LSB mode: Writes to bit 0, then 1, then 2...
                            dst_buf[dst_index] |= 1 << (x % 8)
                        else:
                            dst_buf[dst_index] |= 0x80 >> (x % 8)

            return result
        else:
            raise ValueError(f"Unsupported conversion from {self.mode} with palette {palette.mode}")

    def seg_line(self, x0, y0, x1, y1, color, dash = (5, 3)):
        (segment_on, segment_off) = dash
        dx, dy = x1 - x0, y1 - y0
        xsign = 1 if dx > 0 else -1
        ysign = 1 if dy > 0 else -1
        dx, dy = abs(dx), abs(dy)

        if dx > dy:
            xx, xy, yx, yy = xsign, 0, 0, ysign
        else:
            dx, dy = dy, dx
            xx, xy, yx, yy = 0, ysign, xsign, 0

        decision = 2*dy - dx
        y = 0

        pattern_len, segment_count = segment_on + segment_off, 0

        for x in range(dx + 1):
            # Draw only if we are in the 'on' segment
            # Use modulo to cycle the count, and check if it's less than the 'on' length
            if segment_count % pattern_len < segment_on:
                self.pixel(x0 + x*xx + y*yx, y0 + x*xy + y*yy, color)
            if decision >= 0:
                y += 1
                decision -= 2*dx
            decision += 2*dy
            segment_count += 1

    def seg_vline(self, x, y, h, c, **kwargs):
        self.seg_line(x, y, x, y + h - 1, c, **kwargs)

    def seg_hline(self, x, y, h, c, **kwargs):
        self.seg_line(x, y, x + h - 1, y, c, **kwargs)

    def cross_corners(self, color, x=None, y=None, width=None, height=None, dash = (5, 3)):
        if x is None:
            x = 0
        if y is None:
            y = 0
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        self.seg_line(x, y, x + width - 1, y + height - 1, color, dash=dash)
        self.seg_line(x + width - 1, y, x, y + height - 1, color, dash=dash)

    def rectround(self, x, y, w, h, c, radius, f=False):
        # draw rounded rectangle
        if f:
            # filled
            self.rect(x + radius, y, w - 2 * radius, h, c, True)
            self.rect(x, y + radius, radius, h - 2 * radius, c, True)
            self.rect(x + w - radius, y + radius, radius, h - 2 * radius, c, True)
            self.ellipse(x + radius, y + radius, radius, radius, c, True)
            self.ellipse(x + w - radius - 1, y + radius, radius, radius, c, True)
            self.ellipse(x + radius, y + h - radius - 1, radius, radius, c, True)
            self.ellipse(x + w - radius - 1, y + h - radius - 1, radius, radius, c, True)
        else:
            # outline
            self.hline(x + radius, y, w - 2 * radius, c)
            self.hline(x + radius, y + h - 1, w - 2 * radius, c)
            self.vline(x, y + radius, h - 2 * radius, c)
            self.vline(x + w - 1, y + radius, h - 2 * radius, c)
            self.ellipse(x + radius, y + radius, radius, radius, c, False, 0b0010)
            self.ellipse(x + w - radius - 1, y + radius, radius, radius, c, False, 0b0001)
            self.ellipse(x + radius, y + h - radius - 1, radius, radius, c, False, 0b0100)
            self.ellipse(x + w - radius - 1, y + h - radius - 1, radius, radius, c, False, 0b1000)
        return FrameBufferOffset(self, x, y, w, h)

    def circle(self, x, y, r, c, f=False):
        self.ellipse(x, y, r, r, c, f)

class FrameBufferOffset:
    """
    A wrapper for FrameBufferExtension that applies an (x, y) offset to all drawing operations.

    Attributes:
        fb (FrameBufferExtension): The underlying framebuffer to draw on.
        x (int): The horizontal offset applied to all operations.
        y (int): The vertical offset applied to all operations.
        width (int): The width of the offset region (defaults to fb.width).
        height (int): The height of the offset region (defaults to fb.height).
    """

    def __init__(self, fb: FrameBufferExtension, x: int = 0, y: int = 0, width: int = None, height: int = None):
        self.fb = fb
        self.x, self.y = x, y
        self.width = fb.width if width is None else width
        self.height = fb.height if height is None else height

    def poly(self, x, y, coords: array.array, c, f=None):
        copy = array.array('I', coords)
        for i in range(0, len(copy), 2):
            copy[i] += self.x
            copy[i + 1] += self.y
        return self.fb.poly(x, y, copy, c, f)

    def vline(self, x, y, h, c):
        self.fb.vline(x + self.x, y + self.y, h, c)

    def pixel(self, x: int, y: int) -> int:
        return self.fb.pixel(x + self.x, y + self.y)

    def pixel(self, x: int, y: int, c: int) -> None:
        return self.fb.pixel(x + self.x, y + self.y, c)

    def text(self, s, x, y, c=1):
        self.fb.text(s, x + self.x, y + self.y, c)

    def rect(self, x, y, w, h, c, f=False):
        self.fb.rect(x + self.x, y + self.y, w, h, c, f)

    def scroll(self, xstep, ystep):
        self.fb.scroll(xstep, ystep)

    def ellipse(self, x, y, xr, yr, c, f, m=None):
        if m:
            self.fb.ellipse(x + self.x, y + self.y, xr, yr, c, f, m)
        else:
            self.fb.ellipse(x + self.x, y + self.y, xr, yr, c, f)

    def line(self, x1, y1, x2, y2, c):
        self.fb.line(x1 + self.x, y1 + self.y, x2 + self.x, y2 + self.y, c)

    def blit(self, fbuf, x, y, key=-1, pallet=None):
        self.fb.blit(fbuf, x + self.x, y + self.y, key, pallet)

    def hline(self, x, y, w, c):
        self.fb.hline(x + self.x, y + self.y, w, c)

    def fill(self, c):
        self.fb.rect(self.x, self.y, self.width, self.height, c, True)

    def fill_rect(self, *args, **kwargs):
        return self.fb.fill_rect(*args, **kwargs)

    def textf(self, text, x, y, font: FrameBufferFont, key: int = -1,
              y_spacing: int = 0, x_spacing: int = 0, palette: FrameBufferExtension = None):
        return self.fb.textf(text, x + self.x, y + self.y, font, key, y_spacing, x_spacing, palette)

    def textfalign(self, text, font: FrameBufferFont,
                   align_horiz='center', align_vert='center',
                   left_margin=0, top_margin=0, right_margin=0, bottom_margin=0,
                   **kwargs):
        x, y = FrameBufferExtension.textposition(text,
                                                 self.width, self.height, font,
                                                 align_horiz, align_vert,
                                                 left_margin=left_margin, top_margin=top_margin, right_margin=right_margin, bottom_margin=bottom_margin,
                                                 **kwargs)
        return self.textf(text, x, y, font, **kwargs)

    def triangle(self, x1, y1, x2, y2, x3, y3, color, f=False):
        self.fb.triangle(x1 + self.x, y1 + self.y, x2 + self.x, y2 + self.y, x3 + self.x, y3 + self.y, color, f)

    def invert(self) -> "FrameBufferExtension":
        return self.fb.invert()

    def convert(self, dst_mode: int, palette: "FrameBufferExtension") -> "FrameBufferExtension":
        return self.fb.convert(dst_mode, palette)

    def seg_line(self, x1, y1, x2, y2, color, **kwargs):
        self.fb.seg_line(x1 + self.x, y1 + self.y, x2 + self.x, y2 + self.y, color, **kwargs)

    def seg_vline(self, x, y, h, c, **kwargs):
        self.fb.seg_vline(x + self.x, y + self.y, h, c, **kwargs)

    def seg_hline(self, x, y, h, c, **kwargs):
        self.fb.seg_hline(x + self.x, y + self.y, h, c, **kwargs)

    def cross_corners(self, color, **kwargs):
        kwargs['x'] = self.x + (kwargs['x'] if 'x' in kwargs else 0)
        kwargs['y'] = self.y + (kwargs['y'] if 'y' in kwargs else 0)
        kwargs['width'] = self.width if 'width' not in kwargs else kwargs['width']
        kwargs['height'] = self.height if 'height' not in kwargs else kwargs['height']
        self.fb.cross_corners(color, **kwargs)

    def rectround(self, x, y, w, h, c, radius, f=False):
        return self.fb.rectround(x + self.x, y + self.y, w, h, c, radius, f)

    def circle(self, x, y, r, c, f=False):
        self.fb.circle(x + self.x, y + self.y, r, c, f)

class FontManager:

    FAMILY_LIBERATION = "Liberation"
    CLASSIFICATION_SANS = "Sans"
    CLASSIFICATION_SERIF = "Serif"
    CLASSIFICATION_MONO = "Mono"
    WEIGHT_REGULAR = "Regular"
    WEIGHT_BOLD = "Bold"

    palette = FrameBufferExtension.palette([3, 0, 1, 2], framebuf.GS2_HMSB)
    directory = "fonts"
    cache = {}

    @staticmethod
    def get(family: str = FAMILY_LIBERATION, classification: str = CLASSIFICATION_SANS, weight: str = WEIGHT_REGULAR, size: int = 14, palette: FrameBufferExtension = None):
        font_file = f"{FM.directory}/{family}{classification}-{weight}.{size}.mfnt"
        if not FontManager.cache.get(font_file):
            FM.cache[font_file] = FrameBufferFont(font_file, palette=palette if palette else FM.palette)
        return FM.cache[font_file]

    @staticmethod
    def get_sans(size: int, weight = WEIGHT_REGULAR, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SANS, weight=weight, size=size, palette=palette)
    @staticmethod
    def get_sans_bold(size: int, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SANS, weight=FM.WEIGHT_BOLD, size=size, palette=palette)
    @staticmethod
    def get_sans_regular(size: int, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SANS, weight=FM.WEIGHT_REGULAR, size=size, palette=palette)

    @staticmethod
    def get_serif(size: int, weigth = WEIGHT_REGULAR, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SERIF, weight=weigth, size=size, palette=palette)
    @staticmethod
    def get_serif_bold(size: int, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SERIF, weight=FM.WEIGHT_BOLD, size=size, palette=palette)
    @staticmethod
    def get_serif_regular(size: int, palette: FrameBufferExtension = None):
        return FM.get(classification=FM.CLASSIFICATION_SERIF, weight=FM.WEIGHT_REGULAR, size=size, palette=palette)

FM = FontManager
