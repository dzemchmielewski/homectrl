import array
import atexit
import datetime
import decimal
import functools
import logging
import os
import json
import struct
import sys
import time

import webrepl
import websocket
import termios, select
import readline

from time import sleep
from paho.mqtt.client import Client as PahoMQTTClient, CallbackAPIVersion, MQTTMessageInfo

from common.common import Common
from common.communication import Communication
from configuration import Configuration

class WSCommandLineClient:
    def __init__(self, server_id: str, json_format = True):
        def save(prev_h_len, histfile):
            new_h_len = readline.get_current_history_length()
            readline.set_history_length(10_000)
            readline.append_history_file(new_h_len - prev_h_len, histfile)

        self.server_id = server_id
        self.json_format = json_format
        conf = Configuration.get_config(server_id)
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{conf['host']}:{conf['port']}")
        self.exit = False
        history_file = os.path.join(os.path.expanduser("~"), ".homectrl_ws_history")
        try:
            readline.read_history_file(history_file)
            history_length = readline.get_current_history_length()
        except FileNotFoundError:
            open(history_file, 'wb').close()
            history_length = 0
        atexit.register(save, history_length, history_file)

    def interact(self, command, parse_json=False) -> str:
        self.ws.send(command)
        result = self.ws.recv()
        try:
            if parse_json:
                if self.json_format:
                    return json_serial(json_deserial(result), indent=2, sort_keys=True)
                else:
                    return json_deserial(result)
        except ValueError as e:
            pass
        return result

    def print_lead(self):
        return "[{}][{}]".format(time.strftime("%Y-%m-%d %H:%M:%S"), self.server_id)

    def start(self):
        while not self.exit:
            try:
                str_raw = input(f"{self.print_lead()} >> : ")
            except KeyboardInterrupt:
                str_raw = 'exit'
                print("")
            if str_raw == 'exit':
                self.exit = True
            elif str_raw:
                print(f"{self.print_lead()} << : {self.interact(str_raw, True)}")


class Client(Common):

    def __init__(self, connection: Communication, name="CLIENT", debug=False):
        super().__init__(name, debug=debug)
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

    def close(self):
        self.interact("quit")
        self.conn.close()


class CommandLineClient(Client):

    def __init__(self, connection, name="CMD_CLIENT", format = True, debug=False):
        super().__init__(connection, name=name, debug=debug)
        self.format = format

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

            elif cmd.startswith("*FORMAT"):
                s = cmd.split()
                if len(s) == 2:
                    self.format = s[1] in ("YES", "TRUE", "T", "1", "ON")
                self.log("<<: * {}".format(self.format))

            else:
                if cmd != "":
                    response = self.interact(str_raw)
                    if self.format:
                        try:
                            self.log("<< : \n{}".format(json_serial(json_deserial(response), indent=2)))
                        except ValueError:
                            self.log("<< : {}".format(response))
                    else:
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
        if not os.path.isfile(file) or not os.access(file, os.R_OK):
            self.log("[ERROR]: file not found or not readable")
            return False

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


class WebREPLClient(webrepl.Webrepl):

    class ConsolePosix:
        def __init__(self):
            self.infd = sys.stdin.fileno()
            self.infile = sys.stdin.buffer.raw
            self.outfile = sys.stdout.buffer.raw
            self.orig_attr = termios.tcgetattr(self.infd)

        def enter(self):
            # attr is: [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
            attr = termios.tcgetattr(self.infd)
            attr[0] &= ~(
                    termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON
            )
            attr[1] = 0
            attr[2] = attr[2] & ~(termios.CSIZE | termios.PARENB) | termios.CS8
            attr[3] = 0
            attr[6][termios.VMIN] = 1
            attr[6][termios.VTIME] = 0
            termios.tcsetattr(self.infd, termios.TCSANOW, attr)

        def exit(self):
            termios.tcsetattr(self.infd, termios.TCSANOW, self.orig_attr)

        def readchar(self):
            res = select.select([self.infd], [], [], 0)
            if res[0]:
                return self.infile.read(1)
            else:
                return None

        def write(self, buf):
            self.outfile.write(buf)

    def __init__(self, server_id):
        super().__init__(**{})
        cfg = Configuration.get_config(server_id)

        # if try_exit_homectrl_server:
        #     try:
        #         from backend.tools import Client
        #         print("Connecting to: {}".format(server_id))
        #         client = Client(Configuration.get_communication(server_id), server_id)
        #         print(f" >>  server_exit\n <<  {client.interact('server_exit')}")
        #     except OSError as e:
        #         print("HomeCtrl server is already down")

        port = 8266
        try:
            self.connect(cfg['host'], port)
            self.login(cfg['webrepl_password'])
        except Exception as e:
            print(f"Error connecting to WEBREPL host {cfg['host']} at port {port}:", e)
            raise e

        if not self.connected:
            print("WEBREPL not connected. Check your password!")
            raise Exception("WEBREPL not connected")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def put_file(self, local_file, remote_file):
        sz = os.stat(local_file)[6]
        dest_fname = remote_file.encode("utf-8")
        rec = struct.pack(webrepl.WEBREPL_REQ_S, b"WA", webrepl.WEBREPL_PUT_FILE, 0, 0, sz, len(dest_fname), dest_fname)
        self.ws.write(rec[:10])
        self.ws.write(rec[10:])
        assert self.read_resp() == 0
        cnt = 0
        with open(local_file, "rb") as f:
            while True:
                sys.stdout.write("Sent %d of %d bytes\r" % (cnt, sz))
                sys.stdout.flush()
                buf = f.read(1024)
                if not buf:
                    break
                self.ws.write(buf)
                cnt += len(buf)
        print()
        assert self.read_resp() == 0

    def get_file(self, local_file, remote_file):
        src_fname = remote_file.encode("utf-8")
        rec = struct.pack(webrepl.WEBREPL_REQ_S, b"WA", webrepl.WEBREPL_GET_FILE, 0, 0, 0, len(src_fname), src_fname)
        self.ws.write(rec)
        assert self.read_resp() == 0
        with open(local_file, "wb") as f:
            cnt = 0
            while True:
                self.ws.write(b"\0")
                (sz,) = struct.unpack("<H", self.ws.read(2))
                if sz == 0:
                    break
                while sz:
                    buf = self.ws.read(sz)
                    if not buf:
                        raise OSError()
                    cnt += len(buf)
                    f.write(buf)
                    sz -= len(buf)
                    sys.stdout.write("Received %d bytes\r" % cnt)
                    sys.stdout.flush()
        print()
        assert self.read_resp() == 0

    def do_repl(self):
        print("Use Ctrl-] to exit this shell, Ctrl-\\ to toggle echo mode")
        echo_mode = False
        console = WebREPLClient.ConsolePosix()
        console.enter()
        try:
            while True:
                sel = select.select([console.infd, self.ws.s], [], [])
                c = console.readchar()
                if c:
                    if c == b"\x1d":  # ctrl-], exit
                        break
                    elif c == b'\x1c':  # ctrl-\ to echo mode
                        echo_mode = not echo_mode
                        console.write(f"echo mode is {'ON' if echo_mode else 'OFF'}\n\r".encode())
                    else:
                        if echo_mode:
                            console.write(c)
                        self.ws.writetext(c)
                if self.ws.s in sel[0]:
                    c = self.ws.read(1, text_ok=True)
                    while c is not None:
                        # pass character through to the console
                        oc = ord(c)
                        if oc in (8, 9, 10, 13, 27) or oc >= 32:
                            console.write(c)
                        else:
                            console.write(b"[%02x]" % ord(c))
                        if self.ws.buf:
                            c = self.ws.read(1)
                        else:
                            c = None
        finally:
            console.exit()

    def repl(self, commands: array):
        console = WebREPLClient.ConsolePosix()
        console.enter()
        try:
            for cmd in commands:
                self.ws.writetext(cmd.encode("utf-8") + b"\r\n")
                newline = False
                while True:
                    r = self.ws.read(1024, text_ok=True, size_match=False)
                    # print(f"***{r}***({newline})***")
                    if r == b'>>> ' and newline:
                        break
                    newline = (r == b'\r\n')
                    console.write(r)
        finally:
            console.exit()


class MQTTClient(PahoMQTTClient):
    def __init__(self, on_connect=None, on_disconnect=None, on_message=None, on_publish=None, keepalive:int = None):
        super().__init__(CallbackAPIVersion.VERSION2)
        conf = Configuration.get_mqtt_config()
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.on_publish = on_publish
        self.username_pw_set(conf["username"], conf["password"])
        if keepalive:
            self.keepalive = keepalive
        self.connect(conf["host"], conf["port"])

    def publish(self, *args, **kwargs) -> MQTTMessageInfo:
        if not self.is_connected():
            self.reconnect()
        return super().publish(*args, **kwargs)


class MQTTMonitor:

    TARGET_STATE = ["  ", " M", " S", "MS"]
    logger = logging.getLogger("MQTT")

    def __init__(self, topic):
        self.topic = topic

    def target_state(self, ts):
        if ts in range(0, 4):
            return self.TARGET_STATE[ts]
        return " ?"

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        self.logger.info("[{}] {}".format(msg.topic, message))
        # for line in traceback.format_stack():
        #     print(line.strip())

        try:
            if message:
                data = json_deserial(message)
                if hasattr(data, 'get') and callable(getattr(data, 'get')) and data.get("radar"):

                    self.logger.info("[RADAR][{}][{}][{}][{}][{}][MOV: {:03}cm, {:03}%][STA: {:03}cm, {:03}%][DST: {:03}cm] [{}]".format(
                        msg.topic,
                        " ON" if data["presence"] else "OFF", self.target_state(data["radar"]["target_state"]),
                        ("NIGHT" if data["darkness"] else " DAY ") if data.get("darkness") else " - ",
                        "light  ON" if data["light"] else "light OFF",
                        data["radar"]["move"]["distance"], data["radar"]["move"]["energy"],
                        data["radar"]["static"]["distance"], data["radar"]["static"]["energy"],
                        data["radar"]["distance"], data["presence_read_time"]))
        except BaseException as e:
            self.logger.error("ERROR! {}".format(e))

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.logger.info(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}, TOPIC: {self.topic}")
        if isinstance(self.topic, str):
            client.subscribe(self.topic)
        elif hasattr(self.topic, '__iter__'):
            for t in self.topic:
                client.subscribe(t)

    def on_disconnect(self, *args):
        self.logger.info("DISCONNECTED!")

    def start(self):
        client = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
        client.loop_start()
        try:
            # client.loop_forever()
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()


class HomeCtrlJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date) or isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def json_serial(obj, indent:int = None, sort_keys: bool = False):
    return json.dumps(obj, cls=HomeCtrlJsonEncoder, indent=indent, sort_keys=sort_keys)


def json_deserial(json_str):
    return json.loads(json_str, parse_float=lambda x: round(decimal.Decimal(x), 10))


def singleton(cls):
    instances = {}

    @functools.wraps(cls)
    def wrapper(*args, **kwargs):
        if cls not in instances or instances.get(cls, None).get('args') != (args, kwargs):
            instances[cls] = {
                'args': (args, kwargs),
                'instance': cls(*args, **kwargs)
            }
        return instances[cls].get('instance')

    return wrapper


def run_in_thread(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import threading
        threading.Thread(target=func, args=(args, kwargs)).start()
    return wrapper


def create_n_threads(thread_count=1):
    def wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import threading
            for i in range(thread_count):
                threading.Thread(target=func, args=(args, kwargs)).start()
        return wrapper
    return wrapper
