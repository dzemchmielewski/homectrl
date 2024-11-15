from board.worker import MQTTWorker
from modules.pin_io import PinIO


class WardrobeWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("wardrobe", debug)
        self.door_sensor = PinIO("door", 3)
        self.light_pin = PinIO("light", 4)
        worker_data = self.get_data()
        worker_data.data = {
            "name": self.name,
            "light": None
        }
        worker_data.control = {
            "mode": "auto"  # on, off, auto
        }
        worker_data.loop_sleep = 0.2

    def start(self):
        self.begin()
        worker_data = self.get_data()

        while self.keep_working():
            try:

                publish = False

                # Mode
                if worker_data.control["mode"] == "auto":
                    # Light/Door signal
                    light = self.door_sensor.get_signal()
                elif worker_data.control["mode"] == "on":
                    light = 1
                elif worker_data.control["mode"] == "off":
                    light = 0
                else:
                    raise ValueError("Unknown mode: {}".format(worker_data.control["mode"]))

                # Handle the light
                if light != worker_data.data["light"]:
                    publish = True
                    worker_data.data["light"] = light
                    self.light_pin.set_signal(light)
                worker_data.data["read_light"] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except Exception as e:
                self.handle_exception(e)

        self.end()
