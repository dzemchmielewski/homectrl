from collections import deque

from board.worker import MQTTWorker
from modules.bmp_aht import BMP_AHT
from modules.darkness import DarknessSensor
from modules.pin_io import PinIO
from common.common import time_ms


class DevWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("dev", debug)
        self.darkness = DarknessSensor.from_analog_pin(4)
        self.reader = BMP_AHT.from_pins(2, 1)

        self.led = PinIO("LED", 0)
        self.led.set_signal(0)
        worker_data = self.get_data()
        worker_data.data = {
            "name": self.name,
            "temperature": None,
            "pressure": None,
            "humidity":  None,
            "voltage": None,
            "datetime": None,
            "led": 0
        }
        worker_data.control = {
            "led_modulo": 1,
        }

    def handle_help(self):
        return "DEV WORKER COMMANDS: test"

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd == "TEST":
            answer = "This is TEST answer"
        else:
            answer = "[ERROR] unknown command (DevWorker): {}".format(msg)
        return answer

    def start(self):
        self.begin()
        worker_data = self.get_data()
        previous_sensor_read_time = None
        queue = deque((), 5)
        count = 0

        while self.keep_working():
            try:
                publish = False

                # Handle voltage reading:
                voltage = self.darkness.read_voltage()
                queue.append(voltage)
                lst = list(queue)
                mean = round(sum(lst)/len(lst), 1)
                worker_data.data["datetime"] = self.the_time_str()
                if mean != worker_data.data["voltage"]:
                    publish = True
                    worker_data.data["voltage"] = mean

                # Handle LED:
                count += 1
                if count % worker_data.control["led_modulo"] == 0:
                    worker_data.data["led"] = (worker_data.data["led"] + 1) % 2
                    self.led.set_signal(worker_data.data["led"])
                    count = 0

                # BMP & AHT sensor:
                if previous_sensor_read_time is None or time_ms() - previous_sensor_read_time > (60 * 1_000):
                    readings = self.reader.readings()
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
