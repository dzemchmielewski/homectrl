import machine
from modules.bmp_aht import BMP_AHT
from modules.pzem import PZEM
from board.worker import MQTTWorker
from common.common import time_ms


class BathroomWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("bathroom", debug)
        self.reader = BMP_AHT.from_pins(8, 9)
        self.pzem = PZEM(uart=machine.UART(1, baudrate=9600, tx=7, rx=6))
        worker_data = self.get_data()
        worker_data.data = {
            "name": self.name,
            "temperature": None,
            "pressure": None,
            "humidity":  None,
            "electricity_summary": None,
            "electricity": {
                "voltage": None,
                "current": None,
                "active_power": None,
                "active_energy": None,
                "power_factor": None
            }
        }

    def handle_help(self):
        return "BATHROOM COMMANDS: reset_ae"

    def handle_message(self, msg):
        cmd = msg.strip().upper()
        if cmd == "RESET_AE":
            answer = "TODO: reset Active Energy counter!"
        else:
            answer = "[ERROR] unknown command (BathroomWorker): {}".format(msg)
        return answer

    def start(self):
        self.begin()

        worker_data = self.get_data()

        previous_sensor_read_time = None
        previous_pzem_read_time = None

        while self.keep_working():
            try:
                publish = False

                # BMP & AHT sensor:
                if previous_sensor_read_time is None or time_ms() - previous_sensor_read_time > (60 * 1_000):
                    readings = (self.reader.temperature, self.reader.pressure, self.reader.humidity)
                    if readings != (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]):
                        publish = True
                        (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]) = readings
                    worker_data.data["read_sensor"] = self.the_time_str()
                    previous_sensor_read_time = time_ms()

                # PZEM:
                if previous_pzem_read_time is None or time_ms() - previous_pzem_read_time > (2 * 1_000):
                    self.pzem.read()
                    readings = {
                            "voltage": self.pzem.getVoltage(),
                            "current": round(self.pzem.getCurrent(), 3),
                            # Active Power need to be greater than 0.4 - washing machine takes some small
                            # power periodically what is messing reading history
                            "active_power": round(self.pzem.getActivePower(), 1) if self.pzem.getActivePower() > 0.4 else 0,
                            "active_energy": self.pzem.getActiveEnergy(),
                            "power_factor": round(self.pzem.getPowerFactor(), 2) if self.pzem.getActivePower() > 0.4 else 0
                    }
                    prev = worker_data.data["electricity"]
                    if ((readings["current"], readings["active_power"], readings["active_energy"], readings["power_factor"])
                            != (prev["current"], prev["active_power"], prev["active_energy"], prev["power_factor"])):
                        publish = True
                        worker_data.data["electricity"] = readings

                    worker_data.data["read_electricity"] = self.the_time_str()
                    worker_data.data["electricity_summary"] = self.pzem.to_abbr_str()
                    previous_pzem_read_time = time_ms()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()

            except BaseException as e:
                self.handle_exception(e)

        self.end()
