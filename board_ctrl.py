import os
import sys
from time import sleep
import json
from common.common import Common, CommonSerial, time_ms


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

            elif str == "MONITOR":
                self.handle_monitor()
                expect_read = False
                self.ser.readline()

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

    def handle_monitor(self):
        try:
            while True:
                self.log(self.interact("read"))
                sleep(1.1)
        except (KeyboardInterrupt, EOFError):
            pass


class DataCollector(BoardClient):
    RADAR_DATA_TARGET_STATE = 0
    RADAR_DATA_MOVE_ENERGY = 2
    RADAR_DATA_STAT_ENERGY = 4

    def __init__(self):
        super().__init__()

    def collect_data(self, prev_data, new_data, last_time_save):
        # Collect initial data
        if prev_data is None:
            return True

        # The change of detection, darkness or target state
        # is definitely the change to collect:
        if (prev_data["detection"] != new_data["detection"]
                or prev_data["darkness"] != new_data["darkness"]
                or prev_data["radar"][self.RADAR_DATA_TARGET_STATE] != new_data["radar"][self.RADAR_DATA_TARGET_STATE]):
            return True

        # Collect when movement energy or static energy change is major:
        if (abs(prev_data["radar"][self.RADAR_DATA_MOVE_ENERGY] - new_data["radar"][self.RADAR_DATA_MOVE_ENERGY]) > 60
                or abs(prev_data["radar"][self.RADAR_DATA_STAT_ENERGY] - new_data["radar"][self.RADAR_DATA_STAT_ENERGY]) > 60):
            return True

        # Collect at least one per 5 minutes :
        if last_time_save is None or time_ms() - last_time_save > 5 * 60 * 1_000:
            return True

        # ignore all distances changes:
        return False

    def start(self):
        prev = None
        last_time = None

        try:
            while True:
                data = self.interact("read")
                values = {
                    "detection": data["detection"],
                    "darkness": data["darkness"],
                    "radar": data["radar"][0]
                }
                if self.collect_data(prev, values, last_time):
                    last_time = time_ms()
                    prev = values
                    self.log(values)
                sleep(1)
        except (KeyboardInterrupt, EOFError):
            pass


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "collector":
            DataCollector().start()
        else:
            CommandLineClient().start()
    except (KeyboardInterrupt, EOFError):
        print("EXIT")


