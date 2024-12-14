from board.worker import MQTTWorker
from modules.bmp_aht import BMP_AHT
from modules.ld2410 import LD2410
from modules.pinio import PinIO
from common.common import CommonSerial, time_ms
from modules.radar_control import RadarControl


class ToiletWorker(MQTTWorker):

    def __init__(self, debug=True):
        super().__init__("toilet", debug)
        self.cond_reader = BMP_AHT.from_pins(2, 5)

        self.human_presence = PinIO(3)
        self.light_off_delay = 20 * 1_000
        self.light_switch = PinIO(4, False)

        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=0, rx=1, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)
        self.radar_control = RadarControl(self.radar)

        worker_data = self.get_data()
        worker_data.loop_sleep = 0.3
        worker_data.data = {
            "name": self.name,
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "read_cond_sensor": None,
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

    def handle_help(self):
        return self.radar_control.handle_help()

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd.startswith("RADAR"):
            return self.radar_control.handle_message(" ".join(msg.split()[1:]))
        return "[ERROR] unknown command (ToiletWorker): {}".format(msg)

    def start(self):
        self.begin()

        worker_data = self.get_data()
        is_light_on: bool = False
        floating_time = None
        read_cond_sensor = None

        while self.keep_working():
            try:
                publish = False

                # BMP & AHT sensor:
                if read_cond_sensor is None or time_ms() - read_cond_sensor > (60 * 1_000):
                    readings = self.cond_reader.readings()
                    if readings != (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]):
                        publish = True
                        (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]) = readings
                    worker_data.data["read_cond_sensor"] = self.the_time_str()
                    read_cond_sensor = time_ms()

                # Human radar data:
                # data = self.radar.get_radar_data()
                # while data[0][0] not in range(0, 4):
                #     data = self.radar.get_radar_data()

                # Human detection:
                presence = self.human_presence.get()
                worker_data.data["presence_read_time"] = self.the_time_str()

                # Light management:
                if worker_data.control["mode"] == "on":
                    is_light_on = True

                elif worker_data.control["mode"] == "off":
                    is_light_on = False

                elif worker_data.control["mode"] == "auto":
                    new_light = presence
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
                            if time_ms() - floating_time > self.light_off_delay:
                                is_light_on = False
                                floating_time = None

                else:
                    raise ValueError("Unknown mode: {}".format(worker_data.control["mode"]))

                # Finally make the physical light turn (or not):
                self.light_switch.set(is_light_on)

                # Send current state to MQTT, only when at least one
                # of (presence, is_light_on) has been changed:
                readings = (presence, is_light_on)
                if readings != (worker_data.data["presence"], worker_data.data["light"]):
                    publish = True
                    worker_data.data["presence"] = readings[0]
                    worker_data.data["light"] = readings[1]
                    # worker_data.data["radar"] = {
                    #     "presence": worker_data.data["presence"],
                    #     "target_state": data[0][0],
                    #     "move": {
                    #         "distance": data[0][1],
                    #         "energy": data[0][2]
                    #     },
                    #     "static": {
                    #         "distance": data[0][3],
                    #         "energy": data[0][4]
                    #     },
                    #     "distance": data[0][5]
                    # }

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except Exception as e:
                self.handle_exception(e)

        self.end()

# Initial setup:
#
# radar.edit_detection_params(4, 4, 3)
#
# for i in range(0,8):
#         radar.edit_gate_sensitivity(i, 30, 30)
