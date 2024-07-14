import gc
import os
import ubinascii
import machine
import time
import json
from common.common import Common, CommonSerial

finish_server = False


class CommonServer(Common):

    def __init__(self, name: str, tx_pin: int, rx_pin: int):
        super().__init__(name, False, False)
        self.uart = CommonSerial(id=0, baudrate=76800, bits=8, tx=tx_pin, rx=rx_pin, timeout=2)
        self.id = ubinascii.hexlify(machine.unique_id()).decode()
        self.start_time = time.ticks_ms()
        self.system_status = {
            "id": self.id,
            "name": self.name,
            "freq": machine.freq()/1_000_000,
        }

    def handle_message(self, message):
        return "unknown command: {}".format(message)

    def handle_help(self):
        return ""

    def handle_mkdir(self, msg):
        s = msg.split()
        if len(s) != 2:
            return "[ER] USAGE: MKDIR dirname"
        dirname = s[1]

        try:
            os.mkdir(dirname)
        except BaseException as e:
            return "[ER] {}".format(e)

        return "mkdir completed: {}".format(dirname)

    def handle_ls(self, msg):
        s = msg.split()
        if len(s) != 2:
            return "[ER] USAGE: LS dirname"
        dirname = s[1]

        try:
            return os.listdir(dirname)
        except BaseException as e:
            return "[ER] {}".format(e)

    def handle_put(self, msg):
        s = msg.split()
        if len(s) != 3:
            return "[ER] USAGE: PUT filename size"
        filename = s[1]

        if not s[2].isdigit():
            return "[ER] cannot convert to integer: {}".format(s[1])
        bytes = int(s[2])

        self.uart.write("ready for putting {} bytes to the {} file\n".format(bytes, filename).encode())
        self.uart.flush()

        with open(filename, "w") as f:
            b = None
            while b is None:
                b = self.uart.read(bytes)

            f.write(b.decode())
        return "put completed: {}".format(filename)

    def start(self):
        self.log("START")
        restart = False
        global finish_server

        while not finish_server and not restart:
            b = self.uart.readline()
            if b:
                raw_msg = b.decode()
                self.log("IN : {}".format(raw_msg))
                msg = raw_msg.strip().upper()

                if msg == "UPTIME":
                    answer = "OS up: {}, server up: {}".format(
                        self.format_uptime(time.ticks_ms() // 1000),
                        self.format_uptime((time.ticks_ms() - self.start_time) // 1_000))

                elif msg == "EXIT":
                    finish_server = True
                    answer = "BYE"

                elif msg == "REBOOT":
                    machine.reset()
                    answer = "call reboot"

                elif msg.startswith("PUT"):
                    answer = self.handle_put(raw_msg)

                elif msg.startswith("MKDIR"):
                    answer = self.handle_mkdir(raw_msg)

                elif msg.startswith("LS"):
                    answer = json.dumps(self.handle_ls(raw_msg))

                elif msg == "STATUS":
                    gc.collect()
                    self.system_status["os_uptime"] = time.ticks_ms() // 1000
                    self.system_status["server_uptime"] = (time.ticks_ms() - self.start_time) // 1_000
                    self.system_status["mem_alloc"] = gc.mem_alloc()
                    self.system_status["mem_free"] = gc.mem_free()
                    answer = json.dumps(self.system_status)

                elif msg == "HELP":
                    answer = "COMMON COMMANDS: uptime, status, help, reboot, exit, mkdir, put; {}".format(self.handle_help())

                else:
                    answer = self.handle_message(raw_msg)

                self.log("OUT: {}".format(answer))
                self.uart.write("{}\n".format(answer).encode())
                self.uart.flush()

        self.log("Exit")

