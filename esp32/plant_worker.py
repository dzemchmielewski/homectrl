import json
import machine
from machine import Pin, ADC

from board.mqtt import MQTT
from board.worker import MQTTWorker
from modules.pinio import PinIO


class PlantWorker(MQTTWorker):
    UV_MAX = 2.891
    UV_MIN = 1.2
    # One-hour sleep time:
    SLEEP_TIME_SEC = 60*60

    def __init__(self, debug=False):
        MQTT.KEEPALIVE_SEC = self.SLEEP_TIME_SEC
        super().__init__("plant", debug)
        self.mqtt.mqtt.set_last_will(self.topic_live, json.dumps({"live": False, "error": "last will", "delay": 30}), True)
        self.sensor_power = PinIO(0, True)
        self.test_power = PinIO(8, True)
        self.adc = ADC(Pin(4, mode=Pin.IN))
        self.adc.atten(ADC.ATTN_11DB)

        worker_data = self.get_data()
        worker_data.guard = -1
        worker_data.data = {
            "process": None,
            "moisture": None
        }
        worker_data.control = {
            "sleep": "on"
        }

    def capabilities(self):
        return {
            "controls": [
                {
                    "name": "sleep",
                    "type": "str",
                    "constraints": {
                        "type": "enum",
                        "values": ["on", "off"]
                    }
                }
            ]}

    def start(self):
        self.sensor_power.on()
        self.test_power.on()
        self.begin()
        worker_data = self.get_data()
        loop_index = 0
        loop_size = 10
        moisture = 0

        while self.keep_working() and loop_index < loop_size:
            try:
                publish = False
                loop_index += 1

                # Read the soil moisture:
                voltage = self.adc.read_uv() / 1_000_000
                if voltage <= self.UV_MIN:
                    moisture += 100
                elif voltage >= self.UV_MAX:
                    moisture += 0
                else:
                    moisture += round(((voltage - self.UV_MIN) / (self.UV_MAX - self.UV_MIN) * 100))

                if loop_index + 1 == loop_size:
                    moisture = moisture // loop_size
                    if worker_data.data['moisture'] != moisture:
                        publish = True
                        worker_data.data['moisture'] = moisture

                # Save last process readable time
                worker_data.data["process"] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        # Turn off the sensor power:
        self.sensor_power.off()
        self.test_power.off()

        # Put into the deep sleep:
        if worker_data.control["sleep"] == "on":
            machine.deepsleep(self.SLEEP_TIME_SEC * 1_000)

        self.end()
