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


class Collector(Common):

    def __init__(self, connection: Communication, loop_sleep=60):
        super().__init__("collector")
        self.conn = connection
        self.loop_sleep = loop_sleep
        self.last_value = None
        self.exit = False

    def start(self):
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
            self.log("Error: {}".format(e))
        finally:
            # Exit:
            self.conn.send("exit")
            self.conn.close()

    def read(self) -> dict:
        self.conn.send("read")
        result = self.conn.receive()
        if len(result) == 0:
            raise OSError("Connection to board failed")
        if result.startswith("[ERROR]"):
            return {"error": result}
        return json.loads(result, parse_float=lambda x: round(decimal.Decimal(x), 10))


class CollectorLead:

    def __init__(self, connection: Communication):
        self.collector = Collector(connection)
        self.thread = None

    def start(self):
        self.thread = Thread(target=self.collector.start)
        self.thread.start()

    def stop(self):
        if self.thread.is_alive():
            self.collector.exit = True
            self.thread.join()

    def is_alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def last_value(self) -> dict:
        return self.collector.last_value

    def status(self) -> dict:
        return {
            "is_alive": self.is_alive(),
            "last_value": self.last_value()
        }


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class CollectorServer(CommonServer):

    def __init__(self):
        super().__init__("COLLECTORS",
                         SocketCommunication("conn", "localhost", 9000, is_server=True))

        self.collectors = {
            "kitchen": CollectorLead(SocketCommunication("conn", "192.168.0.121", 8123, read_timeout=30))
        }

        for collector in self.collectors.values():
            collector.start()

    def exit(self):
        for collector in self.collectors.values():
            collector.stop()

    def handle_help(self):
        return "COLLECTORS COMMANDS: list"

    def handle_message(self, msg):
        cmd = msg.strip().upper()

        if cmd == "LIST":
            result = {}
            for name, collector in self.collectors.items():
                result[name] = collector.status()
            answer = json.dumps(result, cls=DateEncoder)

        else:
            answer = "[ERROR] unknown command: {}".format(msg)

        return answer


if __name__ == "__main__":
    collector = CollectorServer()
    try:
        collector.start()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        collector.exit()
