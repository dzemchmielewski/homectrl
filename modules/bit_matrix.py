class BitMatrix:

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.number = 0
        self.bit_format = "{{:#0{}b}}".format(rows * cols + 2)

    def _validate(self, x, y, bit):
        if x < 0 or x >= self.rows or y < 0 or y >= self.cols:
            raise ValueError("Provided coordination: ({}, {}) is out of bounds: ({}, {})".format(x, y, self.rows, self.cols))
        if bit not in [0, 1]:
            raise ValueError("Invalid bit argument. Given: {}, required one off: {}".format(bit, [0, 1]))

    def _get(self, x, y):
        return (self.number >> ((x * self.cols) + y)) & 1

    def _set(self, x, y, bit):
        pos = (x * self.cols) + y
        mask = 1 << pos
        self.number = (self.number & ~mask) | ((bit << pos) & mask)
        return self

    def set(self, x: int, y: int, bit):
        self._validate(x, y, bit)
        return self._set(x, y, bit)

    def get(self, x, y) -> int:
        self._validate(x, y, 0)
        return self._get(x, y)

    def set_row(self, x: int, bits: int):
        if x < 0 or x >= self.rows:
            raise ValueError("Row index out of bounds: {}".format(x))
        if bits < 0 or bits >= (1 << self.cols):
            raise ValueError("Bits value out of bounds: {}".format(bits))
        pos = x * self.cols
        row_mask = ((1 << self.cols) - 1) << pos
        self.number = (self.number & ~row_mask) | ((bits << pos) & row_mask)
        return self

    def __str__(self) -> str:
        rows = [" ".join(["."] + ["|"] + [str(i) for i in range(0, self.cols)]), "-".join(["-"] * 2 + ["-"] * self.cols)]
        for x in range(0, self.rows):
            rows.append(" ".join([str(x), "|"] + [str(self._get(x, y)) for y in range(0, self.cols)]))
        return "\n".join(rows)

    def to_int(self, invert: bool = False) -> int:
        if invert:
            return ~self.number & ((1 << (self.rows * self.cols)) - 1)
        else:
            return self.number

    def to_bits(self) -> str:
        return self.bit_format.format(self.number)

if __name__ == "__main__":
    matrix = BitMatrix(4, 8)
    for i in range(matrix.rows):
        for j in range(matrix.cols):
            matrix.set(i, j, 1)
    # (matrix
    #  .set(0, 1, 1)
    #  .set(3,1,1)
    #  .set(3,2,1)
    #  .set(0,1,1))
    print(matrix)
    print("SIZE: {} x {}, NUMBER: {}, BITS: {}".format(matrix.rows, matrix.cols, matrix.to_int(), matrix.to_bits()))

    n = matrix.to_int()
    for i in range(matrix.rows * matrix.cols):
        print("bit by bit [{}]: {}".format(i, n & 1))
        n = n >> 1