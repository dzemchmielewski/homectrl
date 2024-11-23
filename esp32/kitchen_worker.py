from board.worker import MQTTWorker
from modules.ld2410 import LD2410
from modules.darkness import DarknessSensor
from modules.dht import DHTSensor
from modules.pinio import PinIO
from common.common import CommonSerial, time_ms


class KitchenWorker(MQTTWorker):

    MAX_FLOATING_TIME = 20 * 1_000

    def __init__(self, debug=True):
        super().__init__("kitchen", debug)
        self.dht_sensor = DHTSensor("dht", 5)
        self.darkness_sensor = DarknessSensor.from_analog_pin(2, queue_size=90, voltage_threshold=2.7)
        self.human_presence = PinIO(10)
        self.light_switch = PinIO(0, False)

        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=7, rx=6, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)

        worker_data = self.get_data()
        worker_data.loop_sleep = 0.3
        worker_data.data = {
            "name": self.name,
            "temperature": None,
            "humidity": None,
            "darkness": None,
            "voltage": None,
            "presence": None,
            "light": None
        }
        worker_data.control = {
            "mode": "auto"  # on, off, auto
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
        is_light_on: bool = False
        floating_time = None
        dht_read_time = None
        darkness_read_time = None

        while self.keep_working():
            try:
                publish = False

                # DHT sensor:
                if dht_read_time is None or time_ms() - dht_read_time > (60 * 1_000):
                    readings = (self.dht_sensor.get())
                    if readings != (worker_data.data["temperature"], worker_data.data["humidity"]):
                        publish = True
                        (worker_data.data["temperature"], worker_data.data["humidity"]) = readings
                    worker_data.data["dht_read_time"] = self.the_time_str()
                    dht_read_time = time_ms()

                # Human radar data:
                data = self.radar.get_radar_data()
                while data[0][0] not in range(0, 4):
                    data = self.radar.get_radar_data()

                # Human detection:
                presence = self.human_presence.get()
                worker_data.data["presence_read_time"] = self.the_time_str()

                # Darkness sensor:
                if darkness_read_time is None or time_ms() - darkness_read_time > (5 * 1_000):
                    darkness, mean_voltage, vol = self.darkness_sensor.read_analog()
                    worker_data.data["voltage_momentary"] = vol
                    voltage = round(mean_voltage, 1)
                    if voltage != worker_data.data["voltage"]:
                        publish = True
                        worker_data.data["voltage"] = voltage
                    worker_data.data["darkness_read_time"] = self.the_time_str()
                    darkness_read_time = time_ms()
                else:
                    darkness = worker_data.data["darkness"]

                # Light management:
                if worker_data.control["mode"] == "on":
                    is_light_on = True

                elif worker_data.control["mode"] == "off":
                    is_light_on = False

                elif worker_data.control["mode"] == "auto":
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

                else:
                    raise ValueError("Unknown mode: {}".format(worker_data.control["mode"]))

                # Finally make the physical light turn (or not):
                self.light_switch.set(is_light_on)

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
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except Exception as e:
                self.handle_exception(e)

        self.end()
