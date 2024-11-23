import time
from board.worker import MQTTWorker
from board.boot import Boot
from modules.bmp_aht import BMP_AHT
from modules.darkness import DarknessSensor
from modules.pinio import PinIO
from common.common import time_ms


class DevWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("dev", debug)
        # self.darkness = DarknessSensor.from_analog_pin(4, 5)
        self.reader = BMP_AHT.from_pins(2, 1)

        self.led = PinIO(0)
        self.led.set(0)
        worker_data = self.get_data()
        worker_data.data = {
            "name": self.name,
            "temperature": None,
            "pressure": None,
            "humidity": None,
            "voltage": None,
            "datetime": None,
            "led": False,
            "something_stupid": False
        }
        worker_data.control = {
            "led_modulo": 1,
            "light": "auto"
        }

    def capabilities(self):
        return {
            "controls": [
                {
                    "name": "light",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "off", "auto"]
                    }
                },
                {
                    "name": "led_modulo",
                    "type": "int",
                    "constraints": {
                        "type": "range",
                        "values": {
                            "min": 1,
                            "max": 3600
                        }
                    }
                }
            ]}

    def handle_help(self):
        return "DEV WORKER COMMANDS: stupid"

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd == "STUPID":
            self.get_data().data["something_stupid"] = True
            answer = "You just actually done something quite stupid."
        elif cmd == "TESTBOOT":
            try:
                answer = "Boot: {}".format(Boot.get_instance())
            except Exception as e:
                answer = "exception: " + str(e)
        else:
            answer = "[ERROR] unknown command (DevWorker): {}".format(msg)
        return answer

    def start(self):
        self.begin()
        worker_data = self.get_data()
        previous_sensor_read_time = None
        count = 0

        while self.keep_working():
            try:
                publish = False

                if worker_data.data["something_stupid"]:
                    time.sleep(200)
                    worker_data.data["something_stupid"] = False

                # Handle voltage reading:
                # darkness, mean_voltage, voltage = self.darkness.read_analog()
                # mean = round(mean_voltage, 1)
                # worker_data.data["datetime"] = self.the_time_str()
                # if mean != worker_data.data["voltage"]:
                #     publish = True
                #     worker_data.data["voltage"] = mean

                # Handle LED:
                if worker_data.control["light"] == "on":
                    worker_data.data["led"] = True
                elif worker_data.control["light"] == "off":
                    worker_data.data["led"] = False
                elif worker_data.control["light"] == "auto":
                    count += 1
                    if count % worker_data.control["led_modulo"] == 0:
                        worker_data.data["led"] = not worker_data.data["led"]
                        count = 0
                self.led.set(worker_data.data["led"])

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
