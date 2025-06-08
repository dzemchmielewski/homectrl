import sys
import types

sys.path.append('..')

# Mocking missing modules for testing purposes
fake_module = types.ModuleType("SR74HC595")
fake_module.SR74HC595_Sync = object()

# Register it in sys.modules
sys.modules['SR74HC595'] = fake_module


from segment_lcd8 import ParseForSegments

parser = ParseForSegments(4)

def test(input: str, expected: (str, list)) -> None:
    output = parser.parse(input)
    result = "OK  " if output == expected else "FAIL"
    print(f"{result} \tIN: '{input}', \tOUT: {output}, \tEXPECTED: {expected}")

ParseForSegments.SPACE = '_'
test("1234", ("1234", []))
test("12.34", ("1234", [1]))
test("1.2.3.4.", ("1234", [0,1,2,3]))
test("___.", ("____", [3]))
test("1.2", ("__12", [2]))
test("....", ("____", [0,1,2,3]))
test(".123", ("_123", [0]))
test("1_.23", ("1_23", [1]))
test("1.", ("___1", [3]))
test("_.1._", ("__1_", [1, 2]))

test("123478", ("1234", []))
test("12.3478", ("1234", [1]))
test("1.2.3.4.78", ("1234", [0,1,2,3]))
test("1.2.3.4.7.8", ("1234", [0,1,2,3]))

test("____.78", ("____", [3]))
test("......", ("____", [0,1,2,3]))

