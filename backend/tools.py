import datetime
import decimal
import functools
import os
import json
from time import sleep

from common.common import Common, CommonSerial, time_ms
from common.communication import Communication, SerialCommunication, SocketCommunication
from configuration import Configuration
from paho.mqtt.client import Client as PahoMQTTClient, CallbackAPIVersion


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


class MQTTClient(PahoMQTTClient):
    def __init__(self, on_connect=None, on_disconnect=None, on_message=None, on_publish=None):
        super().__init__(CallbackAPIVersion.VERSION2)
        conf = Configuration.get_mqtt_config()
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.on_publish = on_publish
        self.username_pw_set(conf["username"], conf["password"])
        self.connect(conf["host"], conf["port"])


class MQTTMonitor(Common):

    TARGET_STATE = ["  ", " M", " S", "MS"]

    def __init__(self, topic, debug=False):
        super().__init__("MQTT", debug)
        self.topic = topic

    def target_state(self, ts):
        if ts in range(0, 4):
            return self.TARGET_STATE[ts]
        return " ?"

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        self.log("[{}] {}".format(msg.topic, message))
        # for line in traceback.format_stack():
        #     print(line.strip())

        try:
            if message:
                data = json_deserial(message)
                if data.get("radar"):
                    self.log("[RADAR][{}][{}][{}][{}][{}][MOV: {:03}cm, {:03}%][STA: {:03}cm, {:03}%][DST: {:03}cm] [{}]".format(
                        msg.topic,
                        " ON" if data["presence"] else "OFF", self.target_state(data["radar"]["target_state"]),
                        "NIGHT" if data["darkness"] else " DAY ",
                        "light  ON" if data["light"] else "light OFF",
                        data["radar"]["move"]["distance"], data["radar"]["move"]["energy"],
                        data["radar"]["static"]["distance"], data["radar"]["static"]["energy"],
                        data["radar"]["distance"], data["presence_read_time"]))
        except BaseException as e:
            self.log("ERROR! {}".format(e))

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}, TOPIC: {self.topic}")
        if isinstance(self.topic, str):
            client.subscribe(self.topic)
        elif hasattr(self.topic, '__iter__'):
            for t in self.topic:
                client.subscribe(t)

    def on_disconnect(self, *args):
        self.log("DISCONNECTED!")

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
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def json_serial(obj, indent=None):
    return json.dumps(obj, cls=HomeCtrlJsonEncoder, indent=indent)


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
