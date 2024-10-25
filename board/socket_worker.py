from board.worker import MQTTWorker
from modules.darkness import DarknessSensor
from modules.pin_io import PinIO
from common.common import time_ms


class SocketWorker(MQTTWorker):

    class StatusIndicator:
        def __init__(self, touch: PinIO, red: PinIO):
            self.showTime = None
            self.touch = touch
            self.red = red

        def handle(self):
            if self.touch.get_signal() == 1:
                self.showTime = time_ms()
            elif self.showTime is not None and time_ms() - self.showTime > 5 * 1_000:
                self.showTime = None

            self.red.set_signal(1 if self.showTime else 0)

    def __init__(self, debug=False):
        super().__init__("socket", debug)
        # self.darkness = DarknessSensor.from_analog_pin(4)

        self.relay = PinIO("RELAY", 0)
        self.touch = PinIO("TOUCH", 4)
        self.relay.set_signal(0)
        worker_data = self.get_data()
        worker_data.loop_sleep = 0.2
        worker_data.data = {
            "relay": None
        }
        worker_data.control = {
            "mode": "auto"
        }
        self.status_indicator = SocketWorker.StatusIndicator(self.touch, self.relay)
        worker_data.debug = {
            "showTime": self.status_indicator.showTime
        }

    def capabilities(self):
        return {
            "controls": [
                {
                    "name": "mode",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "off", "auto"]
                    }
                }
            ]}

    def start(self):
        self.begin()
        worker_data = self.get_data()

        while self.keep_working():
            try:
                publish = False

                if worker_data.control["mode"] == "auto":
                    # TODO: implement auto mode
                    relay = worker_data.data["relay"] if worker_data.data["relay"] is not None else 0

                elif worker_data.control["mode"] == "on":
                    relay = 1
                elif worker_data.control["mode"] == "off":
                    relay = 0
                else:
                    raise ValueError("Unknown mode: {}".format(worker_data.control["mode"]))

                # Handle the relay
                if relay != worker_data.data["relay"]:
                    publish = True
                    worker_data.data["relay"] = relay
                    self.relay.set_signal(relay)
                worker_data.data["read"] = self.the_time_str()

                self.status_indicator.handle()
                worker_data.debug["showTime"] = self.status_indicator.showTime
                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()
