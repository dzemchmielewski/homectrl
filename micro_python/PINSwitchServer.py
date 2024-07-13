from machine import UART, Pin

from micro_python.common_server import CommonServer


class PINSwitchServer(CommonServer):

    def __init__(self):
        super().__init__("PINSWSRV", 0, 1)

        self.pin = 16
        self.value = False
        self.gpio.setup_out(self.pin)
        self.gpio.output(self.pin, self.value)

    def handle_help(self):
        return "PIN switch server commands: dev, aaa"

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd == "SW":
            try:
                self.value = not self.value
                self.gpio.output(self.pin, self.value)
                answer = "switch pin {}: {} -> {}".format(self.pin, not self.value, self.value)
            except BaseException as e:
                answer = str(e)

        elif cmd == "DEV":
            try:
                from machine import UART, Pin
                from ld2410.ld2410 import LD2410
                uart = UART(1, baudrate=256000, bits=8, parity=None, stop=1, tx=Pin(4), rx=Pin(5), timeout=1)
                radar = LD2410("LD2410", uart)
                answer = radar.get_radar_data()
            except BaseException as e:
                answer = str(e)
        else:
            answer = "unknown command: {}".format(msg)

        return answer
