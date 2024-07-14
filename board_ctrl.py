import os
from time import sleep
import json
from common.common import Common, CommonSerial


class BoardClient(Common):

    def __init__(self, port="/dev/ttyS0"):
        super(BoardClient, self).__init__("BRDCTRL", debug=False)
        self.ser = CommonSerial(
            port=port,
            baudrate=76800,
            timeout=2)
        status = self.interact("status")
        self.log("Connected to board {}. OS up: {}, server up: {}".format(
            status["id"],
            self.format_uptime(status["os_uptime"]),
            self.format_uptime(status["server_uptime"])))

    def interact(self, command, expected_json = True):
        self.ser.write(command.encode())
        self.ser.flush()
        result = self.ser.readline()
        self.debug("RAW: {}".format(result))
        if len(list(bytes(result))) == 0:
            raise ConnectionError("Connection to board failed")
        if expected_json:
            return json.loads(result.decode())
        return result.decode()


class CommandLineClient(BoardClient):

    def __init__(self):
        super().__init__()
        self.exit = False

    def start(self):
        while not self.exit:
            str_raw = self.input(">> : ")
            expect_read = True
            str = str_raw.strip().upper()

            if str.startswith("PUT"):
                expect_read = self.handle_put(str_raw)

            # elif str == "MONITOR":
            #     value = None
            #     try:
            #         while True:
            #             new_value = self.read()
            #             if new_value != value:
            #                 value = new_value
            #                 print("[MONITOR] {}".format(value))
            #             sleep(0.1)
            #     except KeyboardInterrupt:
            #         expect_read = False
            #         self.ser.readline()

            elif str == "REBOOT":
                self.ser.write(str_raw.encode())
                self.ser.flush()
                self.exit = True
                expect_read = False

            else:
                self.ser.write(str_raw.encode())
                self.ser.flush()

            if expect_read:
                result = self.ser.readline()
                # self.log("RAW: {}".format(result))
                self.log("<< : {}".format(result.decode().strip()))

    def handle_put(self, str):
        s = str.split()
        if len(s) != 2:
            self.log("ERR: file is required")
            return False

        file = s[1]
        self.ser.write("PUT {} {}".format(file, os.stat(file).st_size).encode())
        self.ser.flush()

        # Read 'ready' response:
        self.log("<< : {}".format(self.ser.readline().decode()))
        sleep(0.2)

        with open(file, "rb") as f:
            self.ser.write(f.read())
        self.ser.flush()
        return True


if __name__ == "__main__":
    try:
        CommandLineClient().start()
    except (KeyboardInterrupt, EOFError):
        print("EXIT")


