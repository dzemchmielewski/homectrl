import ustruct

def bits(data: bytearray):
    return  " ".join("{:08b}".format(d) for d in data)


def from_bits(s: str):
    return int(s, 2).to_bytes((len(s) + 7) // 8, 'big')


data_format = "{}00{}0000"
cases = [
    [data_format.format("01100100000000", "011111110000"), 1600, 127],
    [data_format.format("00111110100000", "011001001001"), 1000, 100.5625],
    [data_format.format("11111111111100", "111011000000"), -1, -20],
    [data_format.format("11110000011000", "110010010000"), -250, -55],
    [data_format.format("11110000011000", "110010010000"), -250, -55],
    [data_format.format("11111101111101", "000110101100"), -32.75, 26.75]
]

for case in cases:
    print(f"Testing {case[1]}, {case[2]}: ", end='')
    data = from_bits(case[0])
    temp, refer = ustruct.unpack('>hh', data)
    refer >>= 4
    temp >>= 2
    refer = refer * 0.0625
    temp = temp / 4
    print(f"decoded: {temp}, {refer}")
    assert temp == case[1]
    assert refer == case[2]

