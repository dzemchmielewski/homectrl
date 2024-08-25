import sys
import time

import uio
from machine import SoftI2C, Pin
from modules.bmp280 import *
from modules.ahtx0 import AHT20

from board.mqtt_publisher import MQTTPublisher
from board.worker import Worker
from modules.pin_io import PinIO
from common.common import time_ms


class PantryWorker(Worker):

    def __init__(self, debug=False):
        super().__init__("pantry", debug)
        self.log("INIT")
        self.door_sensor = PinIO("door", 3)

        bus = SoftI2C(Pin(0), Pin(1))
        self.bmp = BMP280(bus, addr=0x77, use_case=BMP280_CASE_HANDHELD_DYN)
        self.aht = AHT20(bus)

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

        worker_data.data["light"] = None
        worker_data.data["temperature"] = None
        worker_data.data["pressure"] = None
        worker_data.data["humidity"] = None

        previous_sensor_read_time = None

        while not worker_data.go_exit:

            try:

                publish = False

                # Light/Door signal
                light = self.door_sensor.get_signal()
                if light != worker_data.data["light"]:
                    publish = True
                    worker_data.data["light"] = light
                worker_data.data["read_light"] = self.the_time_str()

                # BMP & AHT sensor:
                if previous_sensor_read_time is None or time_ms() - previous_sensor_read_time > (60 * 1_000):

                    readings = (
                                round((self.bmp.temperature + self.aht.temperature) / 2, 1),
                                round(self.bmp.pressure / 100, 1),
                                round(self.aht.relative_humidity, 1))

                    if readings != (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]):
                        publish = True
                        worker_data.data["temperature"] = readings[0]
                        worker_data.data["pressure"] = readings[1]
                        worker_data.data["humidity"] = readings[2]
                    worker_data.data["read_sensor"] = self.the_time_str()
                    previous_sensor_read_time = time_ms()

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
