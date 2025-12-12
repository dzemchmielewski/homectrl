import array

import logging
import struct
import framebuf

log = logging.getLogger(__name__)

class _FrameBufferExtension(framebuf.FrameBuffer):
    def __init__(self, width: int, height: int, mode):
        self.width, self.height, self.mode = width, height, mode
        if mode == framebuf.MONO_HLSB or mode == framebuf.MONO_VLSB:
            size = self.width * self.height // 8
        elif mode == framebuf.GS2_HMSB:
            size = self.width * self.height  // 4
        elif mode == framebuf.GS4_HMSB:
            size = self.width * self.height  // 2
        else:
            raise ValueError("Unsupported framebuf mode")
        self.buffer = memoryview(bytearray(size))
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

    def __init__(self, width: int, height: int, mode):
        super().__init__(width, height, mode)

    def textf(self, text, x, y, font: FrameBufferFont, key: int = -1,
                  y_spacing: int = 0, x_spacing: int = 0, invert_colors: bool = False):
        off_x, off_y = 0, 0
        palette = font.palette.invert() if invert_colors and font.palette else font.palette
        for char in text:
            if char == '\n':
                off_x, off_y = 0, off_y + font.height + y_spacing
            else:
                glyph, char_height, char_width = font.get_char(char)
                if glyph is not None:
                    self.blit(glyph, x + off_x, y + off_y, key, palette)
                off_x += x_spacing + char_width
        return x + off_x, y + off_y + font.height

    def triangle(self, x1, y1, x2, y2, x3, y3, color, f=False):
        if f:
            # Simple filled triangle using polygon fill (if available)
            self.poly(x1, y1, array.array('I', [ x1, y1, x2, y2, x3, y3]), color, True)
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

class FrameBufferOffset:

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
        self.fb.fill(c)

    def fill_rect(self, *args, **kwargs):
        return self.fb.fill_rect(*args, **kwargs)

    def textf(self, text, x, y, font: FrameBufferFont, key: int = -1,
              y_spacing: int = 0, x_spacing: int = 0, invert_colors: bool = False):
        return self.fb.textf(text, x + self.x, y + self.y, font, key, y_spacing, x_spacing, invert_colors)

    def triangle(self, x1, y1, x2, y2, x3, y3, color, f=False):
        self.fb.triangle(x1 + self.x, y1 + self.y, x2 + self.x, y2 + self.y, x3 + self.x, y3 + self.y, color, f)
