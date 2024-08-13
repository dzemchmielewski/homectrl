import gc
import os
import json

import time

import common.common
from common.common import Common, time_ms, start_thread
from common.communication import Communication

if common.common.is_esp32():
    import esp32

machine_loaded = False
try:
    import machine
    import ubinascii
    machine_loaded = True
except ImportError as e:
    pass


finish_server = False


class CommonServer(Common):

    def __init__(self, name: str, connection: Communication):
        super().__init__(name, False, False)
        self.conn = connection
        self.start_time = time_ms()
        self.system_status = {
            "name": self.name,
        }
        if machine_loaded:
            self.system_status["id"] = ubinascii.hexlify(machine.unique_id()).decode()
            self.system_status["freq"] = machine.freq()/1_000_000

    def handle_message(self, message):
        return "[ERROR] unknown command: {}".format(message)

    def handle_help(self):
        return ""

    def on_exit(self):
        pass

    def handle_mkdir(self, msg):
        s = msg.split()
        if len(s) != 2:
            return "[ERROR] USAGE: MKDIR dirname"
        dirname = s[1]

        try:
            os.mkdir(dirname)
        except BaseException as e:
            return "[ERROR] {}".format(e)

        return "mkdir completed: {}".format(dirname)

    def handle_ls(self, msg):
        s = msg.split()
        if len(s) != 2:
            return "[ERROR] USAGE: LS dirname"
        dirname = s[1]

        try:
            return os.listdir(dirname)
        except BaseException as e:
            return "[ERROR] {}".format(e)

    def handle_rm(self, msg):
        s = msg.split()
        if len(s) != 2:
            return "[ERROR] USAGE: RM filename/dirname"
        file = s[1]

        try:
            st = os.stat(file)
            if st[0] & 0x4000:  #is directory
                os.rmdir(file)
            else:
                os.remove(file)
            return "rm completed: {}".format(file)
        except BaseException as e:
            return "[ERROR] {}".format(e)

    def handle_put(self, msg):
        s = msg.split()
        if len(s) != 3:
            return "[ERROR] USAGE: PUT filename size"
        filename = s[1]

        if not s[2].isdigit():
            return "[ERROR] cannot convert to integer: {}".format(s[1])
        bytes = int(s[2])

        self.conn.send("Ready for {} bytes transmission to the {} file".format(bytes, filename))

        with open(filename, "wb") as f:
            b = None
            while b is None:
                b = self.conn.receive_bytes(bytes)
                f.write(b)
        return "PUT completed: {}".format(filename)

    def goodbye(self, out: str = "goodbye"):
        self.log("OUT: {}".format(out))
        self.conn.send(out)
        self.conn.close()

    def start(self):
        self.log("START: {}".format(self.conn))
        restart = False
        global finish_server
        finish_server = False

        while not finish_server and not restart:
            try:
                raw_msg = self.conn.receive()
            except OSError as e:
                # This may be read timeout exception
                # Close connection:
                self.log("Error: {}. Sending goodbye and closing connection".format(e))
                raw_msg = None
                self.goodbye("goodbye timeout")

            if raw_msg:
                self.log("IN : {}".format(raw_msg))
                msg = raw_msg.strip().upper()
                answer = None

                if msg == "UPTIME":
                    answer = "OS up: {}, server up: {}".format(
                        self.format_uptime(time_ms() // 1000),
                        self.format_uptime((time_ms() - self.start_time) // 1_000))

                elif msg == "EXIT" or msg == "BYE" or msg == "QUIT":
                    self.goodbye("goodbye")

                elif msg == "SERVER_EXIT":
                    self.goodbye("goodbye & adieu")
                    finish_server = True

                elif msg == "REBOOT":
                    if machine_loaded:
                        self.goodbye("goodbye & see you in next life")
                        time.sleep(1)
                        machine.reset()
                    else:
                        answer = "[ERROR] Cannot reboot"

                elif msg.startswith("PUT"):
                    answer = self.handle_put(raw_msg)

                elif msg.startswith("MKDIR"):
                    answer = self.handle_mkdir(raw_msg)

                elif msg.startswith("LS"):
                    answer = json.dumps(self.handle_ls(raw_msg))

                elif msg.startswith("RM"):
                    answer = json.dumps(self.handle_rm(raw_msg))

                elif msg == "STATUS":
                    gc.collect()
                    self.system_status["os_uptime"] = time_ms() // 1000
                    self.system_status["server_uptime"] = (time_ms() - self.start_time) // 1_000
                    if hasattr(gc, "mem_alloc") and callable(getattr(gc, "mem_alloc")):
                        self.system_status["mem_alloc"] = gc.mem_alloc()
                        self.system_status["mem_free"] = gc.mem_free()
                    if common.common.is_esp32():
                        self.system_status["mcu_temp"] = esp32.mcu_temperature()
                    answer = json.dumps(self.system_status)

                elif msg == "HELP":
                    answer = "COMMON COMMANDS: help, status, uptime, mkdir, put, ls, rm, exit (bye, quit), server_exit, reboot; {}".format(
                        self.handle_help())

                else:
                    answer = self.handle_message(raw_msg)

                if answer is not None:
                    self.log("OUT: {}".format(answer))
                    self.conn.send(answer)

        self.on_exit()
        self.conn.close()
        self.log("Exit")
