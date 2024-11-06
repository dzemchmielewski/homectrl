from board.worker import MQTTWorker
from modules.darkness import DarknessSensor
from modules.pinio import PinIO
from common.common import time_ms


class SocketWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("socket", debug)
        self.darkness = DarknessSensor.from_analog_pin(4, queue_size=1, voltage_threshold=2.31)
        self.relay = PinIO(0, 0)
        self.status_indicator = SocketWorker.StatusIndicator(5, 8, 7, 6)

        worker_data = self.get_data()
        worker_data.loop_sleep = 0.2
        worker_data.data = {
            "relay": None,
            "process": None,
            "darkness": None,
            "debug_voltage": None,
            "touch": None
        }
        worker_data.control = {
            "mode": "auto"
        }

    def capabilities(self):
        return {
            "controls": [
                {
                    "name": "mode",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "auto", "off"]
                    }
                }
            ]}

    def start(self):
        self.begin()
        worker_data = self.get_data()

        while self.keep_working():
            try:
                publish = False

                # Read darkness:
                darkness, mean_voltage, voltage = self.darkness.read_analog()
                worker_data.data["debug_voltage"] = (mean_voltage, voltage)
                if darkness != worker_data.data["darkness"]:
                    worker_data.data["darkness"] = darkness
                    publish = True

                # Set relay:
                if worker_data.control["mode"] == "auto":
                    relay = darkness
                elif worker_data.control["mode"] == "on":
                    relay = 1
                elif worker_data.control["mode"] == "off":
                    relay = 0
                else:
                    raise ValueError("Unknown mode: {}".format(worker_data.control["mode"]))

                # Handle the relay
                relay_changed = False
                if relay != worker_data.data["relay"]:
                    publish = True
                    worker_data.data["relay"] = relay
                    self.relay.set(relay)
                    relay_changed = True

                # Handle lights indicators:
                self.status_indicator.refresh(worker_data.control["mode"], relay, relay_changed)
                worker_data.data["touch"] = self.status_indicator.touch.get()

                # Save last process readable time
                worker_data.data["process"] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()

    class StatusIndicator:
        def __init__(self, touch: int, blue: int, red: int, green: int):
            self.showTime = time_ms()
            self.touch = PinIO(touch)
            self.red = PinIO(red, True)
            self.green = PinIO(green, True)
            self.blue = PinIO(blue, True)

        def refresh(self, mode: str, relay: int, changed: bool):
            if self.touch.get() == 1 or changed:
                self.showTime = time_ms()
            elif self.showTime is not None and time_ms() - self.showTime > 5 * 1_000:
                self.showTime = None

            if self.showTime is None:
                self.red.off()
                self.green.off()
                self.blue.off()
            else:
                if mode == "auto":
                    self.blue.toggle()
                else:
                    self.blue.on()
                if relay:
                    self.green.on()
                    self.red.off()
                else:
                    self.green.off()
                    self.red.on()

