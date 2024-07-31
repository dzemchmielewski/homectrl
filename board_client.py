import os
import json
from common.common import Common, CommonSerial, time_ms
from common.communication import Communication, SerialCommunication, SocketCommunication


class CommandLineClient(Common):

    def __init__(self, connection):
        super().__init__("CMD_BRD_CLNT", connection, True)
        self.conn = connection
        self.exit = False

        self.log("Connecting to server {}...".format(connection))

        status = self.interact("status", expected_json=True)
        self.log("Connected to server {}. OS up: {}, server up: {}".format(
            status["name"],
            self.format_uptime(status["os_uptime"]),
            self.format_uptime(status["server_uptime"])))

    def interact(self, command, expected_json=False) -> str:
        self.conn.send(command)
        result = self.conn.receive()
        if len(result) == 0:
            raise OSError("Connection to board failed")
        if expected_json:
            return json.loads(result)
        return result

    def start(self):
        self.log("start")
        while not self.exit:
            try:
                str_raw = self.input(">> : ")
            except BaseException as e:
                self.log("Exiting. Reason: {}".format(e))
                str_raw = "exit"

            cmd = str_raw.strip().upper()
            if cmd.startswith("PUT"):
                self.handle_put(str_raw)

            else:
                if cmd != "":
                    response = self.interact(str_raw)
                    self.log("<< : {}".format(response))
                    if response.upper().startswith("GOODBYE"):
                        self.exit = True

            # elif str == "MONITOR":
            #     self.handle_monitor()
            #     expect_read = False
            #     self.ser.readline()
            #
            # if str == "REBOOT":
            #     self.conn.send(str_raw.encode())
            #     self.exit = True
            #     expect_read = False
            #
            # else:

    def handle_put(self, str):
        s = str.split()
        if len(s) != 2:
            self.log("[ERROR]: file is required")
            return False

        file = s[1]
        answer = self.interact("PUT {} {}".format(file, os.stat(file).st_size))

        # 'ready' response:
        self.log("<< : {}".format(answer))

        with open(file, "rb") as f:
            self.conn.send_bytes(f.read())

        self.log("<< : {}".format(self.conn.receive()))

        return True
    #
    # def handle_monitor(self):
    #     try:
    #         while True:
    #             self.log(self.interact("read"))
    #             sleep(1.1)
    #     except (KeyboardInterrupt, EOFError):
    #         pass


if __name__ == "__main__":
    try:

        # conn = SocketCommunication("SOCKET", "localhost", 8123, is_server=False, debug=True)
        conn = SocketCommunication("SOCKET", "192.168.0.121", 8123, is_server=False, debug=False)
        # conn = SerialCommunication("SERIAL", CommonSerial(port="/dev/ttyS0", baudrate=76800))
        CommandLineClient(conn).start()

        # if len(sys.argv) > 1 and sys.argv[1] == "collector":
        #     DataCollector().start()
        # else:
        #     CommandLineClient().start()
    except (KeyboardInterrupt, EOFError):
        print("EXIT")
