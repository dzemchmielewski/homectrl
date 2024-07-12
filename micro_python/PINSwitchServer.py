from micro_python.common_server import CommonServer


class PINSwitchServer(CommonServer):

    def __init__(self):
        super().__init__(0, 1)

        self.pin = 16
        self.value = False
        self.gpio.setup_out(self.pin)
        self.gpio.output(self.pin, self.value)

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd == "AAA":
            try:
                self.value = not self.value
                self.gpio.output(self.pin, self.value)
                answer = "switch pin {}: {} -> {}".format(self.pin, not self.value, self.value)
            except BaseException as e:
                answer = str(e)

        elif cmd == "DEV":
            try:
                answer = "dev todo"
            except BaseException as e:
                answer = str(e)
        else:
            answer = "unknown command: {}".format(msg)

        return answer
