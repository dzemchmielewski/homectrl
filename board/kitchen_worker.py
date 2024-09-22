from collections import deque

import time
import uio
import sys
from board.worker import Worker
from board.mqtt_publisher import MQTTPublisher
from modules.ld2410 import LD2410
from modules.darkness import DarknessSensor
from modules.dht import DHTSensor
from modules.pin_io import PinIO
from common.common import CommonSerial, time_ms


class KitchenWorker(Worker):

    MAX_FLOATING_TIME = 20 * 1_000

    def __init__(self, debug=True):
        super().__init__("kitchen", debug)
        self.log("INIT")
        self.darkness_threshold = 2.7
        self.dht_sensor = DHTSensor("dht", 5)
        self.darkness_sensor = DarknessSensor.from_analog_pin(2)
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

    @staticmethod
    def the_time_str() -> str:
        t = time.localtime()
        return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(t[0], t[1], t[2], t[3], t[4], t[5], 0)

    def start(self):
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.loop_sleep = 0.3
        worker_data.data["name"] = self.name
        worker_data.data["temperature"] = None
        worker_data.data["humidity"] = None
        worker_data.data["darkness"] = None
        worker_data.data["voltage"] = None
        worker_data.data["presence"] = None
        worker_data.data["light"] = None
        queue = deque((), 90)

        try:
            self.mqtt = MQTTPublisher(self.name)
            worker_data.mqtt_connected = self.mqtt.connected
        except BaseException as e:
            self.handle_exception(e)

        is_light_on: bool = False
        floating_time = None
        dht_read_time = None
        darkness_read_time = None

        while not worker_data.go_exit:

            try:

                publish = False

                # DHT sensor:
                if dht_read_time is None or time_ms() - dht_read_time > (60 * 1_000):
                    readings = (self.dht_sensor.get())
                    if readings != (worker_data.data["temperature"], worker_data.data["humidity"]):
                        publish = True
                        worker_data.data["temperature"] = readings[0]
                        worker_data.data["humidity"] = readings[1]
                    worker_data.data["dht_read_time"] = self.the_time_str()
                    dht_read_time = time_ms()

                # Human radar data:
                data = self.radar.get_radar_data()
                while data[0][0] not in range(0, 4):
                    data = self.radar.get_radar_data()

                # Human detection:
                presence = self.human_presence.get_signal()
                worker_data.data["presence_read_time"] = self.the_time_str()

                # Darkness sensor:
                if darkness_read_time is None or time_ms() - darkness_read_time > (5 * 1_000):
                    vol = self.darkness_sensor.read_voltage()
                    queue.append(vol)
                    worker_data.data["voltage_momentary"] = vol
                    lst = list(queue)
                    voltage = round(sum(lst)/len(lst), 1)
                    if voltage != worker_data.data["voltage"]:
                        publish = True
                        worker_data.data["voltage"] = voltage
                    worker_data.data["darkness_read_time"] = self.the_time_str()
                    darkness_read_time = time_ms()
                else:
                    voltage = worker_data.data["voltage"]
                darkness = (voltage >= self.darkness_threshold)

                # Light management:
                new_light = darkness and presence
                if not is_light_on and new_light:
                    # Turn on the light immediately, if darkness and presence
                    is_light_on = True
                    floating_time = None

                elif is_light_on == new_light:
                    floating_time = None

                else:
                    # The last case - the light is on and can be turned off
                    # however, not immediately
                    if not floating_time:
                        floating_time = time_ms()

                    else:
                        if time_ms() - floating_time > self.MAX_FLOATING_TIME:
                            is_light_on = False
                            floating_time = None

                # Finally make the physical light turn (or not):
                self.light_switch.set_signal(is_light_on)

                # Send current state to MQTT, only when at least one
                # of (darkness, presence, is_light_on) has been changed:
                readings = (darkness, presence, is_light_on)
                if readings != (worker_data.data["darkness"], worker_data.data["presence"], worker_data.data["light"]):
                    publish = True
                    worker_data.data["darkness"] = readings[0]
                    worker_data.data["presence"] = readings[1]
                    worker_data.data["light"] = readings[2]
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

                if publish:
                    self.mqtt.publish(worker_data.data)
                else:
                    self.mqtt.ping()

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
