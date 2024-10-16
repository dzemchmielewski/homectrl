import _thread
import sys

from board.mqtt_publisher import MQTTPublisher
from common.common import Common, time_ms, start_thread
from common.server import CommonServer
from common.communication import Communication
import json
import time
import uio

_thread.stack_size(1024 * 16)


class WorkerData:
    def __init__(self):
        self.is_alive = False
        self.go_exit = False
        self.loop_sleep = 1
        self.mqtt = False
        self.error = None
        self.data = {
        }
        self.control = {
        }


worker_data = WorkerData()


class Worker(Common):

    def __init__(self, name, debug=True):
        super().__init__(name, debug)
        self.log("INIT")

    def start(self):
        self.log("START")
        global worker_data
        worker_data.is_alive = True

        while not worker_data.go_exit:
            worker_data.data["time_ms"] = time_ms()
            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")

    def begin(self):
        self.log("BEGIN")
        worker_data = self.get_data()
        worker_data.is_alive = True

    def keep_working(self):
        worker_data = self.get_data()
        if not worker_data.go_exit:
            time.sleep(worker_data.loop_sleep)
        return not worker_data.go_exit

    def end(self):
        worker_data = self.get_data()
        worker_data.is_alive = False
        self.log("END")

    @staticmethod
    def get_data() -> WorkerData:
        global worker_data
        return worker_data

    @staticmethod
    def the_time_str() -> str:
        t = time.localtime()
        return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(t[0], t[1], t[2], t[3], t[4], t[5], 0)

    def handle_exception(self, exception):
        traceback = uio.StringIO()
        sys.print_exception(exception, traceback)
        worker_data = self.get_data()
        worker_data.error = traceback.getvalue()
        worker_data.go_exit = True

    def handle_help(self):
        return ""

    def handle_message(self, msg):
        return "[ERROR] unknown command (DevWorker): {}".format(msg)


class MQTTWorker(Worker):
    def __init__(self, name, debug=False):
        super().__init__(name, debug)
        self.mqtt = MQTTPublisher(self.name)
        worker_data = self.get_data()
        worker_data.mqtt = self.mqtt.connected
        worker_data.error = self.mqtt.error

    def mqtt_publish(self):
        worker_data = self.get_data()
        self.mqtt.publish(worker_data.data)
        worker_data.mqtt = self.mqtt.connected
        worker_data.error = self.mqtt.error

    def mqtt_ping(self):
        self.mqtt.ping()
        worker_data = self.get_data()
        worker_data.mqtt = self.mqtt.connected
        worker_data.error = self.mqtt.error

    def handle_exception(self, exception):
        super().handle_exception(exception)
        worker_data = self.get_data()
        self.mqtt.publish({
            "live": False,
            "error": worker_data.error
        }, self.mqtt.live_topic, True)
        worker_data.mqtt = self.mqtt.connected

    def begin(self):
        super().begin()
        self.mqtt.connect()
        worker_data.mqtt = self.mqtt.connected
        worker_data.error = self.mqtt.error

    def end(self):
        self.mqtt.close()
        worker_data.mqtt = self.mqtt.connected
        super().end()


class WorkerServer(CommonServer):

    def __init__(self, name, communication: Communication, worker: Worker = None):
        super().__init__(name, communication)
        self.worker = worker if worker else Worker("NoneWorker")
        self.worker_handle_message = False
        worker_data = self.worker.get_data()
        if not hasattr(worker_data, 'launch_on_start') or worker_data.launch_on_start:
            start_thread(self.worker.start)

    def on_exit(self):
        worker_data = self.worker.get_data()
        if worker_data.is_alive:
            worker_data.go_exit = True

    def handle_help(self):
        return "WORKER SERVER COMMANDS: go, nogo, info, read, control; {}".format(self.worker.handle_help())

    def handle_message(self, msg):
        worker_data = self.worker.get_data()

        cmd = msg.strip().upper()

        if cmd == "GO":
            if self.worker is not None:
                if worker_data.is_alive:
                    answer = "[ERROR] worker was already started..."
                else:
                    worker_data.go_exit = False
                    start_thread(self.worker.start)
                    answer = "call worker start: {}".format(self.worker)
            else:
                answer = "[ERROR] worker class is None"

        elif cmd == "NOGO":
            if worker_data.is_alive:
                worker_data.go_exit = True
                answer = "call worker exit"
            else:
                answer = "[ERROR] worker is not alive..."

        elif cmd == "INFO":
            answer = json.dumps(worker_data.__dict__)

        elif cmd == "READ":
            try:
                answer = json.dumps(worker_data.data)
            except Exception as e:
                answer = str(e)

        elif cmd.startswith("CONTROL"):
            try:
                s = msg.split()
                name = s[1]
                value = type(worker_data.control[name])(s[2])
                worker_data.control[name] = value
                answer = f'[OK] {name}: {value}'
            except Exception as exc:
                worker_data.control.keys()
                answer = "[ERROR] {}: {}; USAGE: control {{{}}} value".format(exc.__class__.__name__, exc, ", ".join(worker_data.control.keys()))

        else:
            answer = self.worker.handle_message(msg)

        return answer


if __name__ == '__main__':
    try:
        Worker("DummyWorker").start()
    except KeyboardInterrupt:
        pass

