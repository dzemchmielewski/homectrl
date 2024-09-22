from collections import deque

import sys
import time

import uio
from board.mqtt_publisher import MQTTPublisher
from board.worker import Worker
from modules.darkness import DarknessSensor


class DevWorker(Worker):

    def __init__(self, debug=False):
        super().__init__("dev", debug)
        self.log("INIT")
        self.darkness = DarknessSensor.from_analog_pin(4)
        self.mqtt = MQTTPublisher(self.name)

    def handle_exception(self, exception):
        traceback = uio.StringIO()
        sys.print_exception(exception, traceback)
        worker_data = self.get_data()
        worker_data.error = traceback.getvalue()
        worker_data.is_alive = False
        worker_data.go_exit = True

    @staticmethod
    def the_time_str() -> str:
        t = time.localtime()
        return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(t[0], t[1], t[2], t[3], t[4], t[5], 0)

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name
        worker_data.data["voltage"] = None
        worker_data.data["datetime"] = None
        queue = deque((), 90)

        while not worker_data.go_exit:

            try:

                publish = False

                voltage = self.darkness.read_voltage()
                queue.append(voltage)
                lst = list(queue)
                mean = round(sum(lst)/len(lst), 1)
                worker_data.data["datetime"] = self.the_time_str()
                if mean != worker_data.data["voltage"]:
                    publish = True
                    worker_data.data["voltage"] = mean

                if publish:
                    self.mqtt.publish(worker_data.data)
                else:
                    self.mqtt.ping()

                time.sleep(worker_data.loop_sleep)

            except BaseException as e:
                self.handle_exception(e)
                self.mqtt.publish_error(worker_data.error)

        try:
            self.mqtt.close()
        except BaseException as e:
            self.log("Error while closing MQTT: {}".format(e))

        worker_data.is_alive = False
        self.log("EXIT")
