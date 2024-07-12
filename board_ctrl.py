import os
from time import sleep
import json
import serial
from common.common import Common


class BoardClient(Common):

    def __init__(self, port="/dev/ttyS0"):
        super(BoardClient, self).__init__("BRDCTRL")
        self.ser = serial.Serial(
            port=port,
            baudrate=76800,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=2)

    def read(self):
        self.ser.write("read".encode())
        self.ser.flush()
        result = self.ser.readline()
        # self.log("RAW: {}".format(result))
        #self.log("<< : {}".format(result.decode().strip()))
        return json.loads(result.decode())


class CommandLineClient(BoardClient):

    def __init__(self):
        super().__init__()

    def start(self):
        while True:
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
    except KeyboardInterrupt:
        print("EXIT")
