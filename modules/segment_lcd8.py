import logging
import time
from SR74HC595 import SR74HC595_Sync as SR74HC595
from bit_matrix import BitMatrix

log = logging.getLogger(__name__)

class ParseForSegments:
    DOT = '.'
    SPACE = ' '
    def __init__(self, segments: int = 4):
        self.segments = segments
        self.elements = []

    def parse(self, text: str):
        self.elements = []
        for c in text:
            if not self._append(c):
                break
        return self._get()

    class Element:
        def __init__(self, char: str, dot: bool = False, completed: bool = False):
            self.char = char
            self.dot = dot
            self.completed = completed

    def _append(self, c) -> bool:
        if c == self.DOT:
            if len(self.elements) > 0 and not self.elements[-1].completed:
                self.elements[-1].dot = True
                self.elements[-1].completed = True
            else:
                self.elements.append(self.Element(self.SPACE, dot=True, completed=True))
        else:
            if len(self.elements) < self.segments:
                if len(self.elements) > 0 and not self.elements[-1].completed:
                    self.elements[-1].completed = True
                self.elements.append(self.Element(c))
            else:
                return False
        return len(self.elements) < self.segments or (len(self.elements) == self.segments and not self.elements[-1].completed)

    def _get(self) -> (str, list):
        pad = [self.Element(self.SPACE)] * (self.segments - len(self.elements))
        result = pad + self.elements
        return  ''.join([e.char for e in result]), [i for i, e in enumerate(result) if e.dot]

class SegmentLCD8:

    # segments layout:
    #      -1-
    #     |     |
    #     6     2
    #     |     |
    #      -7-
    #     |     |
    #     5     3
    #     |     |
    #      -4-  .8 (dot)

    SEGMENTS = {
        # Digits
        '0': 0b11111100,
        '1': 0b01100000,
        '2': 0b11011010,
        '3': 0b11110010,
        '4': 0b01100110,
        '5': 0b10110110,
        '6': 0b10111110,
        '7': 0b11100000,
        '8': 0b11111110,
        '9': 0b11110110,

        # Uppercase letters
        'A': 0b11101110,
        'B': 0b00111110,
        'C': 0b10011100,
        'D': 0b01111010,
        'E': 0b10011110,
        'F': 0b10001110,
        'G': 0b10111100,
        'H': 0b01101110,
        'I': 0b01100000,
        'J': 0b01111000,
        'L': 0b00011100,
        'N': 0b00101010,
        'O': 0b11111100,
        'P': 0b11001110,
        'Q': 0b11100110,
        'R': 0b00001010,
        'S': 0b10110110,
        'T': 0b00011110,
        'U': 0b01111100,
        'Y': 0b01110110,
        'Z': 0b11011010,

        # Lowercase letters (distinct where useful)
        'a': 0b11111010,
        'b': 0b00111110,
        'c': 0b00011010,
        'd': 0b01111010,
        'e': 0b11011110,
        'f': 0b10001110,
        'h': 0b00101110,
        'i': 0b00100000,
        'j': 0b01111000,
        'l': 0b00001100,
        'n': 0b00101010,
        'o': 0b00111010,
        'r': 0b00001010,
        's': 0b10110110,
        't': 0b00011110,
        'u': 0b00111000,
        'y': 0b01110110,

        # Symbols
        '-': 0b00000010,
        '_': 0b00010000,
        ' ': 0b00000000,
        '.': 0b00000001,
    }
    # SEGMENTS = {
    #     ' ': 0b00000000, '0': 0b11111100, '1': 0b01100000, '2': 0b11011010,
    #     '3': 0b11110010, '4': 0b01100110, '5': 0b10110110, '6': 0b10111110,
    #     '7': 0b11100000, '8': 0b11111110, '9': 0b11110110,
    #     'A': 0b11101110, 'B': 0b00111110, 'C': 0b10011100, 'D': 0b01111010, 'E': 0b10011110,
    #     'F': 0b10001110, '_': 0b00010000,
    #     'H': 0b01101110, 'L': 0b00011100, 'P': 0b11001110, '-': 0b00000010,
    #     'R': 0b00001010, 'U': 0b01111100, '=': 0b10010000,
    #     'N': 0b00101010, 'O': 0b11111100, 'o': 0b00111010,
    #     '(': 0b10011100, ')': 0b11110000,
    # }

    def __init__(self, shift_register: SR74HC595, segments: int = 4):
        self.shift_register = shift_register
        self.matrix = BitMatrix(segments, 8)
        self.parser = ParseForSegments(segments)

    def ch2byte(self, char: str) -> int:
        return self.SEGMENTS.get(char, self.SEGMENTS.get(char.upper(), 0))

    def set(self, text: str):
        chars, dot_positions = self.parser.parse(text)
        log.debug(f"chars and dot positions: '{chars}', {dot_positions}")
        for (i, char) in enumerate(chars):
            self.matrix.set_row(self.matrix.rows - i - 1, self.ch2byte(char))
        for pos in dot_positions:
            self.matrix.set(self.matrix.rows - pos - 1, 0, 1)
        log.debug("\n" + str(self.matrix))
        self.shift_register.set(self.matrix.to_int(True))

    def clear(self):
        self.set('')

    def flow(self):
        bit = 0
        self.matrix.number = 0
        self.shift_register.set(self.matrix.to_int(True))
        while True:
            bit = 1 - bit
            for i in range(4):
                for j in range(8):
                    self.shift_register.set(self.matrix.set(i, j, bit).to_int(True))
                    time.sleep(1)


if __name__ == "__main__":
    log.setLevel(logging.DEBUG)
    lcd = SegmentLCD8(SR74HC595(8*4, 7, 8, 9), segments=4)

    # text = deque([], 4)
    # while True:
    #     text.append(input("Enter 1 char:")[:1].upper())
    #     chars = ''.join(text)
    #     logging.info(f"Setting LCD to: {chars}")
    #     lcd.set(chars)

    # import random
    # while True:
    #     num = "{:04d}".format(random.randint(0, 9999))
    #     logging.info(f"Setting LCD to: {num}")
    #     lcd.set(num)
    #     time.sleep(0.5)

    # try:
    #     i = 0
    #     while True:
    #         lcd.set(str(i))
    #         i = (i + 1) % 10_000
    #         time.sleep_ms(10)
    # except KeyboardInterrupt:
    #     pass

    chars = ''
    while chars != 'exit':
        chars = input("Enter text (or 'exit'):")
        logging.error(f"Setting LCD to: '{chars}'")
        lcd.set(chars)
    lcd.clear()
