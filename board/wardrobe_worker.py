import time
from board.mqtt_publisher import MQTTPublisher
from board.worker import Worker
from modules.pin_io import PinIO


class WardrobeWorker(Worker):

    def __init__(self, debug=False):
        super().__init__("wardrobe", debug)
        self.log("INIT")
        self.door_sensor = PinIO("door", 3)
        self.light_pin = PinIO("light", 4)
        self.mqtt = MQTTPublisher(self.name)

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name
        worker_data.data["light"] = None
        worker_data.loop_sleep = 0.2

        while not worker_data.go_exit:

            try:

                publish = False

                # Light/Door signal
                light = self.door_sensor.get_signal()
                if light != worker_data.data["light"]:
                    publish = True
                    worker_data.data["light"] = light
                    self.light_pin.set_signal(light)
                worker_data.data["read_light"] = self.the_time_str()

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
