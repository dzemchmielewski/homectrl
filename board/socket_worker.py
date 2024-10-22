from board.worker import MQTTWorker
from modules.darkness import DarknessSensor
from modules.pin_io import PinIO
from common.common import time_ms


class SocketWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("socket", debug)
        # self.darkness = DarknessSensor.from_analog_pin(4)

        self.led = PinIO("RELAY", 0)
        self.led.set_signal(0)
        worker_data = self.get_data()
        worker_data.data = {
            "relay": 0
        }
        worker_data.control = {
            "relay": "auto"
        }

    def capabilities(self):
        return {
            "controls": [
                {
                    "name": "relay",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "off", "auto"]
                    }
                }
            ]}

    def start(self):
        self.begin()
        # worker_data = self.get_data()
        # previous_sensor_read_time = None

        while self.keep_working():
            try:
                publish = False

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()
            except BaseException as e:
                self.handle_exception(e)

        self.end()
