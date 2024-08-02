import decimal
import json
import datetime
from threading import Thread
from time import sleep
from timeit import default_timer as timer

import storage
from common.common import Common
from common.communication import Communication, SocketCommunication
from common.server import CommonServer
from homectrl import Configuration


class Collector(Common):

    def __init__(self, connection: Communication, loop_sleep=60):
        super().__init__(connection.name)
        self.conn = connection
        self.loop_sleep = loop_sleep
        self.last_value = None
        self.exit = True

    def start(self):
        self.exit = False
        try:
            while not self.exit:
                data = self.read()
                if (error := data.get("error")) is not None:
                    self.log(error)
                else:
                    data["timestamp"] = datetime.datetime.now()
                    self.last_value = data
                    storage.save(data)

                start_sleep = timer()
                while not self.exit and timer() - start_sleep < self.loop_sleep:
                    sleep(1)

        except BaseException as e:
            self.log("[ERROR] while reading board: {}".format(e))
        finally:
            # Exit:
            try:
                self.conn.send("exit")
                self.conn.close()
            except BaseException as e:
                self.log("[ERROR] while closing connection: {}".format(e))

    def read(self) -> dict:
        self.conn.send("read")
        result = self.conn.receive()
        if len(result) == 0:
            raise OSError("Connection to board failed")
        if result.startswith("[ERROR]"):
            return {"error": result}
        return json.loads(result, parse_float=lambda x: round(decimal.Decimal(x), 10))


class CollectorLead(Common):

    def __init__(self, connection: Communication):
        super().__init__(connection.name)
        self.log("Starting collector lead")
        self.collector = Collector(connection)
        self.collector_thread = None
        self.pasture_exit = False
        self.pasture_thread = Thread(target=self.pasture)
        self.pasture_thread.start()

    def start(self):
        if not self.is_collector_alive():
            self.log("Starting collector thread")
            self.collector_thread = Thread(target=self.collector.start)
            self.collector_thread.start()

    def stop(self):
        if self.collector_thread.is_alive():
            self.log("Stopping collector thread")
            self.collector.exit = True
            self.collector_thread.join()

    def pasture(self):
        while not self.pasture_exit:
            if not self.is_collector_alive() and not self.collector.exit:
                self.log("Trying to resume collector")
                self.start()

            start_sleep = timer()
            while not self.pasture_exit and timer() - start_sleep < 15:
                sleep(1)

    def stop_pasture(self):
        if self.pasture_thread.is_alive():
            self.pasture_exit = True
            self.pasture_thread.join()

    def is_collector_alive(self) -> bool:
        return self.collector_thread is not None and self.collector_thread.is_alive()

    def last_value(self) -> dict:
        return self.collector.last_value

    def status(self) -> dict:
        return {
            "collector_is_alive": self.is_collector_alive(),
            "collector_exit": self.collector.exit,
            "pasture_is_alive": self.pasture_thread.is_alive(),
            "pasture_exit": self.pasture_exit,
            "last_value": self.last_value(),
        }


class HomeCtrlJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


class CollectorServer(CommonServer):

    def __init__(self):
        conf = Configuration.MAP["collector"]
        super().__init__("COLLECTOR",
                         SocketCommunication("conn", conf["host"], conf["port"], is_server=True, debug=conf["debug"]))
        self.collectors = {}
        for k, v in Configuration.MAP["board"].items():
            if v["collect"]:
                self.collectors[k] = CollectorLead(SocketCommunication(k, v["host"], v["port"], read_timeout=30))
        for coll in self.collectors.values():
            coll.start()

    def on_exit(self):
        for coll in self.collectors.values():
            coll.stop()
            coll.stop_pasture()

    def handle_help(self):
        return "COLLECTOR COMMANDS: list, go, nogo"

    def handle_message(self, msg):
        cmd = msg.strip().upper()

        if cmd == "LIST" or cmd == "INFO":
            result = {}
            for name, collector in self.collectors.items():
                result[name] = collector.status()
            answer = result

        elif cmd.startswith("GO") or cmd.startswith("NOGO"):
            if len(msg.split()) != 2:
                answer = {"error": "Invalid arguments"}
            else:
                collector = msg.split()[1]
                if collector not in self.collectors.keys():
                    answer = {"error": "No such collector: {}"}
                else:
                    self.collectors[collector].start() if cmd.startswith("GO") else self.collectors[collector].stop()
                    answer = self.collectors[collector].status()

        else:
            answer = {"error": "Unknown command: {}".format(msg)}

        return json.dumps(answer, cls=HomeCtrlJsonEncoder)


if __name__ == "__main__":
    collector = CollectorServer()
    try:
        collector.start()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        collector.on_exit()
