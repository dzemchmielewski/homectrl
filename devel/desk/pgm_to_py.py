import sys

if len(sys.argv) < 2:
    print("Usage: pgm_to_py.py <pgm file>")
    sys.exit(1)

debug = True
pgm_file = sys.argv[1]

width, height = (None, None)
data = []

with open(pgm_file, "r") as f:
    assert "P2" == f.readline().strip()

    while width is None or height is None:
        line = f.readline().strip()
        if not line.startswith("#"):
            width, height = map(int, line.split())

    if debug:
        print("Width: {}, Height: {}".format(width, height))

    assert "255" == f.readline().strip()

    while line := f.readline().strip():
        if not line.startswith("#"):
            data.extend(map(int, line.split()))

if debug:
    print("Data (len={}): {}".format(len(data), data))

# grayscale 8 bit  -> 4 bit
for i in range(len(data)):
    data[i] = (data[i] + 1)//16 if data[i] != 255 else 15

if debug:
    print("Data (len={}): {}".format(len(data), data))

with open("test.pgm", "w") as f:
    f.write("P2\n{} {}\n16\n".format(width, height))
    for d in data:
        f.write("{} ".format(d))

print("_data = \\")
for row in range(height):
    print("b'", end='')
    for col in range(0, width, 2):
        high, low = data[row*width+col], data[row*width+col+1] if col + 1 < width else 0
        byte = high << 4 | low
        print("\\x{:02x}".format(byte), end='')
    print("'\\")

print("")
print("_mvdata = memoryview(_data)")
print("")
print("def data():")
print("    return _mvdata")
