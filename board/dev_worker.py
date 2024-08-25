import sys
import time
import uio
from board.mqtt_publisher import MQTTPublisher
from board.worker import Worker


class DevWorker(Worker):

    def __init__(self, debug=True):
        super().__init__("dev", debug)
        self.log("INIT")
        self.mqtt = None

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        try:
            self.mqtt = MQTTPublisher(self.name, "test")
            worker_data.mqtt_connected = self.mqtt.connected
            worker_data.data["debug"] = self.mqtt.debug_message
        except BaseException as e:
            traceback = uio.StringIO()
            sys.print_exception(e, traceback)
            worker_data.error = traceback.getvalue()
            worker_data.is_alive = False
            worker_data.go_exit = True
            worker_data.data["debug"] = self.mqtt.debug_message

        while not worker_data.go_exit:

            try:
                worker_data.data["time"] = time.localtime()
                self.mqtt.publish(worker_data.data)
                worker_data.mqtt_connected = self.mqtt.connected
                worker_data.data["debug"] = self.mqtt.debug_message
                time.sleep(worker_data.loop_sleep)

            except BaseException as e:
                traceback = uio.StringIO()
                sys.print_exception(e, traceback)
                worker_data.error = traceback.getvalue()
                worker_data.is_alive = False
                worker_data.go_exit = True
                self.mqtt.publish_error(worker_data.error)
                worker_data.data["debug"] = self.mqtt.debug_message

        try:
            self.mqtt.close()
        except BaseException as e:
            self.log("Error while closing MQTT: {}".format(e))

        worker_data.is_alive = False
        self.log("EXIT")
