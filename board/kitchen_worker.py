import time
import uio
import sys
from board.worker import Worker
from board.mqtt_publisher import MQTTPublisher
from ld2410 import LD2410
from modules.darkness import DarknessSensor
from modules.dht import DHTSensor
from modules.pin_io import PinIO
from common.common import CommonSerial, time_ms


class KitchenWorker(Worker):

    MAX_FLOATING_TIME = 20 * 1_000

    def __init__(self, debug=True):
        super().__init__("kitchen", debug)
        self.log("INIT")
        self.dht_sensor = DHTSensor("dht", 7)
        self.last_dht_read = None
        self.darkness_sensor = DarknessSensor("darkness", 9)
        self.human_presence = PinIO("human", 10)
        self.light_switch = PinIO("light", 0)
        self.light_switch.set_signal(False)

        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=7, rx=6, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)

        self.mqtt = None

    def handle_exception(self, exception):
        traceback = uio.StringIO()
        sys.print_exception(exception, traceback)
        worker_data = self.get_data()
        worker_data.error = traceback.getvalue()
        worker_data.is_alive = False
        worker_data.go_exit = True

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        try:
            self.mqtt = MQTTPublisher(self.name)
            worker_data.mqtt_connected = self.mqtt.connected
        except BaseException as e:
            self.handle_exception(e)

        is_light_on: bool = False
        floating_time = None
        # TODO: previous values - send data, only
        #  when those values changed
        # previous_values = {
        #     "darkness": None,
        #     "presence": None,
        #     "light": None
        # }

        while not worker_data.go_exit:

            try:
                # # DHT sensor:
                # if self.last_dht_read is None or time_ms() - self.last_dht_read > 60:
                #     temp, hum = self.dht_sensor.get()
                #     worker_data.data["temperature"] = temp
                #     worker_data.data["humidity"] = hum
                #     worker_data.data["dht_time"] = time.localtime()
                #     self.last_dht_read = time_ms()

                # Human radar data:
                data = self.radar.get_radar_data()
                while data[0][0] not in range(0, 4):
                    data = self.radar.get_radar_data()

                # Human detection:
                presence = self.human_presence.get_signal()

                # Darkness sensor:
                darkness = self.darkness_sensor.is_darkness()

                # Light management:
                new_light = darkness and presence
                if not is_light_on and new_light:
                    # Turn on the light immediately, if darkness and presence
                    is_light_on = True
                    floating_time = None

                elif is_light_on == new_light:
                    floating_time = None

                else:
                    # The last case - the light is on but can be turned off
                    # but not immediately
                    if not floating_time:
                        floating_time = time_ms()

                    else:
                        if time_ms() - floating_time > self.MAX_FLOATING_TIME:
                            is_light_on = False
                            floating_time = None

                # Finally make the physical light turn (or not):
                self.light_switch.set_signal(is_light_on)

                # Send current state to MQTT:
                # self.mqtt.ping()
                worker_data.data["darkness"] = darkness
                worker_data.data["presence"] = presence
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
                worker_data.data["light"] = is_light_on
                worker_data.data["time"] = time.localtime()

                self.mqtt.publish(worker_data.data)
                worker_data.mqtt_connected = self.mqtt.connected
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
