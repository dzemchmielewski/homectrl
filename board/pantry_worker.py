from modules.bmp_aht import BMP_AHT

from board.worker import MQTTWorker
from modules.pin_io import PinIO
from common.common import time_ms


class PantryWorker(MQTTWorker):

    def __init__(self, debug=False):
        worker_data = self.get_data()
        worker_data.guard = True
        super().__init__("pantry", debug)
        self.door_sensor = PinIO("door", 3)
        self.reader = BMP_AHT.from_pins(0, 1)
        worker_data.data = {
            "name": self.name,
            "light": None,
            "temperature": None,
            "pressure": None,
            "humidity": None
        }

    def start(self):
        self.begin()
        worker_data = self.get_data()
        previous_sensor_read_time = None

        while self.keep_working():
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

                    readings = (self.reader.temperature, self.reader.pressure, self.reader.humidity)

                    if readings != (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]):
                        publish = True
                        (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]) = readings

                    worker_data.data["read_sensor"] = self.the_time_str()
                    previous_sensor_read_time = time_ms()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()
