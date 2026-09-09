class BitMatrix:

    def __init__(self, rows: int, cols: int, value: int | None = None):
        self.rows = rows
        self.cols = cols
        self.number = value if value is not None and value >= 0 else 0
        self.bit_format = "{{:#0{}b}}".format(rows * cols + 2)

    def get(self, y: int | None = None, x: int | None = None) -> int:
        if x is None and y is None:
            return self.number

        if x is not None and (x < 0 or x >= self.cols):
            raise ValueError(f"Column index out of bounds: {x}")
        if y is not None and (y < 0 or y >= self.rows):
            raise ValueError(f"Row index out of bounds: {x}")

        if y is None and x is not None:
            return self._get_col(x)
        elif y is not None and x is None:
            return self._get_row(y)

        # both x,y are not None
        assert x is not None and y is not None
        return self._get(y, x)

    def set(self, value: int, y: int | None = None, x: int | None = None) -> "BitMatrix":
        if value is None or value < 0:
            raise ValueError(f"Value must be non-negative: {value}")
        if x is not None and (x < 0 or x >= self.cols):
            raise ValueError(f"Column index out of bounds: {x}")
        if y is not None and (y < 0 or y >= self.rows):
            raise ValueError(f"Row index out of bounds: {y}")

        if x is None and y is None:
            self.number = value
            return self

        if x is None and y is not None:
            return self._set_row(value, y)
        elif x is not None and y is None:
            return self._set_col(value, x)

        # both x,y are not None
        assert x is not None and y is not None
        return self._set(value, x, y)


    def _get(self, y: int, x: int) -> int:
        pos = (self.rows * self.cols - 1) - (y * self.cols + x)
        return (self.number >> pos) & 1

    def _set(self, bit, x: int, y: int):
        pos = (self.rows * self.cols - 1) - (y * self.cols + x)
        mask = 1 << pos
        self.number = (self.number & ~mask) | ((bit << pos) & mask)
        return self

    def _get_row(self, y: int) -> int:
        if y < 0 or y >= self.rows:
            raise ValueError("Row index out of bounds: {}".format(y))
        pos = self.cols * (self.rows - 1 - y)
        row_mask = (1 << self.cols) - 1
        return (self.number >> pos) & row_mask

    def _set_row(self, bits: int, y: int):
        if y < 0 or y >= self.rows:
            raise ValueError("Row index out of bounds: {}".format(y))
        if bits < 0 or bits >= (1 << self.cols):
            raise ValueError("Bits value out of bounds: {}".format(bits))
        pos = self.cols * (self.rows - 1 - y)
        row_mask = ((1 << self.cols) - 1) << pos
        self.number = (self.number & ~row_mask) | ((bits << pos) & row_mask)
        return self

    def _get_col(self, x: int) -> int:
        if x < 0 or x >= self.cols:
            raise ValueError("Column index out of bounds: {}".format(x))
        result = 0
        for y in range(self.rows):
            pos = (self.rows * self.cols - 1) - (y * self.cols + x)
            bit = (self.number >> pos) & 1
            result = (result << 1) | bit
        return result

    def _set_col(self, bits: int, x: int):
        if x < 0 or x >= self.cols:
            raise ValueError("Column index out of bounds: {}".format(x))
        if bits < 0 or bits >= (1 << self.rows):
            raise ValueError("Bits value out of bounds: {}".format(bits))
        for y in range(self.rows):
            bit = (bits >> (self.rows - 1 - y)) & 1
            pos = (self.rows * self.cols - 1) - (y * self.cols + x)
            mask = 1 << pos
            self.number = (self.number & ~mask) | ((bit << pos) & mask)
        return self


    def __str__(self) -> str:
        rows = [" ".join(["."] + ["|"] + [str(i) for i in range(0, self.cols)]), "-".join(["-"] * 2 + ["-"] * self.cols)]
        for x in range(0, self.rows):
            rows.append(" ".join([str(x), "|"] + [str(self._get(x, y)) for y in range(0, self.cols)]))
        return "\n".join(rows)

    def __eq__(self, value: object, /) -> bool:
        if value is None:
            return False
        if not isinstance(value, BitMatrix):
            raise TypeError("Value is not a BitMatrix")
        return (self.rows, self.cols, self.number) == (value.rows, value.cols, value.number)

    def to_int(self, invert: bool = False) -> int:
        if invert:
            return ~self.number & ((1 << (self.rows * self.cols)) - 1)
        else:
            return self.number

    def to_bits(self) -> str:
        return self.bit_format.format(self.number)

if __name__ == "__main__":
    F2='{0:02b}'
    F8='{0:08b}'
    F16='{0:08b}'

    matrix = BitMatrix(3, 8)
    for i in range(matrix.rows):
        for j in range(matrix.cols):
            matrix.set(0, i, j)
    (matrix
     .set(1, 0, 0)
     .set(1,0,1)
     .set(1,0,2)
     .set(1,0,3)
     .set(1,0,4)
     .set(1,0,5)
    .set(1,0,6))
    matrix.set(0b11111111, y=1)
    matrix.set(0b011, x = 7)

    print(matrix)
    print("SIZE: {} x {}, NUMBER: {}, BITS: {}".format(matrix.rows, matrix.cols, matrix.to_int(), matrix.to_bits()))

    # by rows:
    assert matrix.get(0) == 0b11111110
    assert matrix.get(1) == 0b11111111
    assert matrix.get(2) == 0b00000001

    #by cols:
    for i in range(matrix.cols - 1):
        assert matrix.get(x=i) == 0b110
    # last one column is different:
    assert matrix.get(x=matrix.cols - 1) == 0b011

    # n = matrix.to_int()
    # for i in range(matrix.rows * matrix.cols):
    #     print("bit by bit [{}]: {}".format(i, n & 1))
    #     n = n >> 1

    m2 = BitMatrix(2,8, (0b10110011 << 8) | 0b00011101)

    print(f"M2: {m2.number}")
    print(m2)

    # print("Columns:")
    # for i in range(m2.cols):
    #     print(f"{F2.format(m2.get(x=i))}, ", end = '')
    # print('')

    m3 = BitMatrix(2,8, (0b10110011 << 8) | 0b00011101)
    assert m2 == m3
    m3.set(0, 0, 0)
    assert (m2 == m3) == False
    m2.set(0, 0, 0)
    assert m2 == m3

    print("====================================")
    m3 = BitMatrix(2,8, (0b00110111 << 8) | 0b01011100)
    xor = BitMatrix(2, 8, m2.number ^ m3.number)
    print(f"M2: {m2.number}, {m2.to_bits()}")
    print(m2)
    print(f"M3: {m3.number}, {m3.to_bits()}")
    print(m3)
    print(f"M2 xor M3: {xor.number}, {xor.to_bits()}")
    print(xor)
