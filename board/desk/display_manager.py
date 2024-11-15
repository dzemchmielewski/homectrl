import framebuf
from machine import SPI, Pin

from board.desk.framebuf_writer import Writer
from board.desk.ssd1327 import SSD1327_SPI
import board.desk.dejavu24 as font24
import board.desk.background as background
import board.desk.digits_big as digits_big


class DeskDisplayManager(framebuf.FrameBuffer):

    def __init__(self):
        self.width = 128
        self.height = 96
        self.background = background.data()
        _digits = digits_big.data()
        self.digits = []
        for i in range(10):
            self.digits.append(framebuf.FrameBuffer(bytearray(_digits[i*13*30:(i+1)*13*30]), 26, 30, framebuf.GS4_HMSB))

        self.buffer = bytearray(self.background)
        # self.buffer = bytearray(self.width*self.height//2)

        super().__init__(self.buffer, self.width, self.height, framebuf.GS4_HMSB)
        self.bg_color = 0
        self.fg_color = 15
        self.writer = Writer(self, font24)
        self.writer_pos = self.writer._getstate()

    def reset(self):
        # Writer.set_textpos(self, 0, 0)
        self.set_pos(0, 0)
        for i in range(len(self.buffer)):
            self.buffer[i] = self.background[i]

    def set_style(self, fg_color=None, bg_color=None, font = None):
        if fg_color is not None:
            self.fg_color = fg_color
        if bg_color is not None:
            self.bg_color = bg_color
        if font is not None:
            self.writer.font = font

    def move_pos(self, pos_row=None, pos_col=None):
        if pos_row is not None:
            self.writer_pos.text_row = self.writer_pos.text_row + pos_row
        if pos_col is not None:
            self.writer_pos.text_col = self.writer_pos.text_col + pos_col

    def set_pos(self, pos_row=None, pos_col=None):
        if pos_row is not None:
            self.writer_pos.text_row = pos_row
        if pos_col is not None:
            self.writer_pos.text_col = pos_col

    def before_char_blit(self, buffer, width, height):
        result = bytearray((width if width % 2 == 0 else width+1)*height//2)
        bytes_per_row = (width - 1)//8 + 1
        i = 0
        for row in range(height):
            for col in range(0, width, 2):
                byte = buffer[row * bytes_per_row + col // 8]
                high = (byte & (1 << (7 - (col % 8)))) > 0
                low = (byte & (1 << (7 - ((col+1) % 8)))) > 0 if col + 1 < width else False
                result[i] = ((self.fg_color if high else self.bg_color) << 4) | (self.fg_color if low else self.bg_color)
                i += 1
        return framebuf.FrameBuffer(result, width, height, framebuf.GS4_HMSB)

    def refresh(self, data: dict):
        self.reset()

        self.blit(self.digits[data["channel"]], 7, 7)

        self.set_style(font=font24, fg_color=15)

        self.set_pos(48, 28)
        self.writer.printstring("{:6.3f}".format(data["values"][0]))

        self.set_pos(71, 28)
        self.writer.printstring("{:6.4f}".format(data["values"][1]))

        return self.buffer


class OledDisplay_1_32(SSD1327_SPI):

    # ex: OledDisplay_1_32(1, 19, 22, 23, 18, 5, manager)
    def __init__(self, id: int, sck: int, mosi: int, cs: int, dc: int, res: int, manager: DeskDisplayManager):
        super().__init__(manager.width, manager.height,
                                   SPI(id, sck=Pin(sck), mosi=Pin(mosi)),
                                   Pin(dc), Pin(res), Pin(cs),
                                   buffer=manager.buffer)


if __name__ == "__main__":

    class FileOutputDisplay:
        def __init__(self, manager: DeskDisplayManager):
            self.manager = manager
            self.file_num = 1
            self.filename = "test.pgm"

        def show(self):
            filename = "/tmp/{}{}".format(self.file_num, self.filename)
            f = open(filename, "w")
            f.write("P2" + "\n{} {}\n16\n".format(self.manager.width, self.manager.height))
            w = self.manager.width // 2
            for i in range(self.manager.height):
                for j in range(w):
                    byte = manager.buffer[i*w+j]
                    high, low = byte >> 4, byte & 0x0F
                    f.write("{:3}{:3}".format(high, low))
                f.write("\n")
            f.close()
            self.file_num += 1
            print("File written to: {}".format(filename))


    values = [[18.0, 0.0], [5.1, 0.200], [12.987, 0.001], [18.999, 6.33]]

    manager = DeskDisplayManager()
    output = FileOutputDisplay(manager)

    for i in range(len(values)):
        manager.refresh({
            "channel": i,
            "values": values[i]
        })
        output.show()

    manager.fill(0)
    for i in range(16):
        manager.rect(i*8,0, ((i+1) * 8) - 1 , 96, i, True)
    output.show()