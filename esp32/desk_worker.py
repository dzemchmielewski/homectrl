from machine import Pin, SoftI2C
from common.common import time_ms

from board.worker import MQTTWorker
from board.desk.display_manager import DeskDisplayManager, OledDisplay_1_32
from modules.ina3221 import *


class DeskWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("desk", debug)

        worker_data = self.get_data()
        worker_data.guard = -1
        worker_data.loop_sleep = 0.2
        worker_data.data = {
            "name": self.name,
            "process": None,
            "screen_refresh": None,
            "display": {
                "operational": [None for _ in range(3)],
                "values": [
                    [0, 0] for _ in range(9)
                ],
                "channel": 0
            }
        }

        self.manager = DeskDisplayManager()
        self.screen = OledDisplay_1_32(1, 19, 22, 23, 18, 5, self.manager)

        self.ina = []
        for i, bus in enumerate([
                SoftI2C(scl=Pin(16), sda=Pin(17), freq=400000),
                SoftI2C(scl=Pin(0), sda=Pin(4), freq=400000),
                SoftI2C(scl=Pin(15), sda=Pin(2), freq=400000)]):
            ina = INA3221(bus, i2c_addr=0x40 + i)
            self.ina.append(ina)
            try:
                ina.update(reg=C_REG_CONFIG,
                               mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
                               value=C_AVERAGING_128_SAMPLES | C_VBUS_CONV_TIME_8MS | C_SHUNT_CONV_TIME_8MS | C_MODE_SHUNT_AND_BUS_CONTINOUS)
                for c in range(3):
                    ina.enable_channel(c + 1)
                worker_data.data["display"]["operational"][i] = True

            except Exception as e:
                worker_data.data["display"]["operational"][i] = False
                self.handle_exception(e, False)

    def handle_help(self):
        return "DESK COMMANDS: channel, guard"

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd.startswith("CHANNEL"):
            s = msg.split()
            if len(s) != 2 or not s[1].isdigit():
                return "[ERROR] USAGE: CHANNEL number"
            c = int(s[1])
            data = self.get_data().data["display"]
            if c < 0 or c >= len(data["values"]):
                return "[ERROR] USAGE: CHANNEL number (0 - {})".format(len(data["values"]) - 1)
            data["channel"] = c
            answer = "Channel changed to: {}".format(c)
        elif cmd == "GUARD":
            self.get_data().guard = None
        else:
            answer = "[ERROR] unknown command (Desk): {}".format(msg)
        return answer

    def start(self):
        self.begin()
        worker_data = self.get_data()
        displayed = {
            "channel": None,
            "values": [None, None]
        }

        while self.keep_working():
            try:
                publish = False

                # TODO: Read INA values:
                # ina = self.ina[0]
                # while not ina.is_ready:
                #     print(".",end='')
                #     time.sleep(0.1)
                #     print("")
                # if ina.is_channel_enabled(1):
                #     bus_voltage = ina.bus_voltage(1)
                #     shunt_voltage = ina.shunt_voltage(1)
                #     current = ina.current(1)
                #     data = worker_data.data["display"]
                #     data["values"][0][0] = bus_voltage + shunt_voltage
                #     data["values"][0][1] = current

                # Display channel values:
                data = worker_data.data["display"]
                if (data["channel"] != displayed["channel"]
                        or data["values"][data["channel"]] != displayed["values"]):
                    displayed["channel"] = data["channel"]
                    displayed["values"] = data["values"][data["channel"]]
                    self.manager.refresh(displayed)
                    self.screen.poweron()
                    self.screen.show()
                    worker_data.data["screen_refresh"] = time_ms()

                # Turn off display after 2 minutes:
                if worker_data.data["screen_refresh"] and time_ms() - worker_data.data["screen_refresh"] > 120 * 1_000:
                    self.screen.poweroff()

                # Save last process readable time
                worker_data.data["process"] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()
            except BaseException as e:
                self.handle_exception(e)

        self.screen.poweroff()
        self.end()
