import time
import uio
import sys
from board.worker import Worker
from board.mqtt_publisher import MQTTPublisher
from ld2410 import LD2410
from modules.darkness import DarknessSensor
from modules.dht import DHTSensor
from modules.pin_io import PinIO
from common.common import CommonSerial


class KitchenWorker(Worker):
    TARGET_STATE = [".", "M", "S", "B"]

    def __init__(self, debug=True):
        super().__init__("kitchen", debug)
        self.log("INIT")
        self.dht_sensor = DHTSensor("dht", 7)
        self.last_dht_read = None
        self.darkness_sensor = DarknessSensor("darkness", 9)
        self.human_presence = PinIO("human", 10)
        self.light_switch = PinIO("light", 0)
        self.light_switch.set_signal(0)
        self.previous_values = {
            "darkness": None,
            "presence": None,
            "target_state": None
        }

        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=7, rx=6, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)

        self.mqtt = None

    def resolve_target_state(self, state):
        if state < 0 or state > 3:
            return "?"
        return self.TARGET_STATE[state]

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        try:
            self.mqtt = MQTTPublisher(self.name)
            worker_data.mqtt_connected = self.mqtt.connected
        except BaseException as e:
            traceback = uio.StringIO()
            sys.print_exception(e, traceback)
            worker_data.error = traceback.getvalue()
            worker_data.is_alive = False
            worker_data.go_exit = True

        while not worker_data.go_exit:

            try:
                # # DHT sensor:
                # if self.last_dht_read is None or time_ms() - self.last_dht_read > 60:
                #     temp, hum = self.dht_sensor.get()
                #     worker_data.data["temperature"] = temp
                #     worker_data.data["humidity"] = hum
                #     worker_data.data["dht_time"] = time.localtime()
                #     self.last_dht_read = time_ms()

                # Darkness sensor:
                worker_data.data["darkness"] = self.darkness_sensor.is_darkness()

                # Human radar data:
                data = self.radar.get_radar_data()
                while data[0][0] not in range(0, 4):
                    data = self.radar.get_radar_data()

                # Human detection:
                worker_data.data["presence"] = self.human_presence.get_signal()

                worker_data.data["radar"] = {
                    "presence": worker_data.data["presence"],
                    "target_state": data[0][0],
                    "move": {
                        "distance": data[0][1],
                        "energy": data[0][2]
                    },
                    "static": {
                        "distance": data[0][3],
                        "energy": data[0][4]
                    },
                    "distance": data[0][5]
                }
                worker_data.data["time"] = time.localtime()

                new_values = {"darkness": worker_data.data["darkness"],
                    "presence": worker_data.data["presence"],
                    "target_state": worker_data.data["radar"]["target_state"]}

                if new_values != self.previous_values:
                    # At least one of the three parameters has changed
                    # Manage the light

                    # TODO: should we also take a target_state into consideration?
                    light = worker_data.data["darkness"] and worker_data.data["presence"]

                    worker_data.data["light"] = light
                    self.light_switch.set_signal(light)
                    self.previous_values = new_values

                # Testing for now. Instead of ping send data every second:
                # self.mqtt.ping()
                self.mqtt.publish(worker_data.data)
                worker_data.mqtt_connected = self.mqtt.connected

                time.sleep(worker_data.loop_sleep)

            except BaseException as e:
                traceback = uio.StringIO()
                sys.print_exception(e, traceback)
                worker_data.error = traceback.getvalue()
                worker_data.is_alive = False
                worker_data.go_exit = True
                self.mqtt.publish_error(worker_data.error)

        try:
            self.mqtt.close()
        except BaseException as e:
            self.log("Error while closing MQTT: {}".format(e))

        worker_data.is_alive = False
        self.log("EXIT")
