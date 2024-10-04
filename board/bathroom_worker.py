import time
import machine
from modules.bmp_aht import BMP_AHT
from modules.pzem import PZEM
from board.mqtt_publisher import MQTTPublisher
from board.worker import Worker
from common.common import time_ms


class BathroomWorker(Worker):

    def __init__(self, debug=False):
        super().__init__("bathroom", debug)
        self.log("INIT")
        self.reader = BMP_AHT.from_pins(8, 9)
        self.pzem = PZEM(uart=machine.UART(1, baudrate=9600, tx=7, rx=6))
        self.mqtt = MQTTPublisher(self.name)

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
        self.log("START")

        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        worker_data.data["temperature"] = None
        worker_data.data["pressure"] = None
        worker_data.data["humidity"] = None
        worker_data.data["electricity"] = {
            "voltage": None,
            "current": None,
            "active_power": None,
            "active_energy": None,
            "power_factor": None
        }
        worker_data.data["electricity_summary"] = None

        previous_sensor_read_time = None
        previous_pzem_read_time = None

        while not worker_data.go_exit:

            try:
                publish = False

                # BMP & AHT sensor:
                if previous_sensor_read_time is None or time_ms() - previous_sensor_read_time > (60 * 1_000):
                    readings = (self.reader.temperature, self.reader.pressure, self.reader.humidity)
                    if readings != (worker_data.data["temperature"], worker_data.data["pressure"], worker_data.data["humidity"]):
                        publish = True
                        worker_data.data["temperature"] = readings[0]
                        worker_data.data["pressure"] = readings[1]
                        worker_data.data["humidity"] = readings[2]
                    worker_data.data["read_sensor"] = self.the_time_str()
                    previous_sensor_read_time = time_ms()


                # PZEM:
                if previous_pzem_read_time is None or time_ms() - previous_pzem_read_time > (5 * 1_000):
                    self.pzem.read()
                    readings = {
                            "voltage": round(self.pzem.getVoltage(), 0),
                            "current": self.pzem.getCurrent(),
                            "active_power": self.pzem.getActivePower(),
                            "active_energy": self.pzem.getActiveEnergy(),
                            "power_factor": self.pzem.getPowerFactor()
                    }
                    if readings != worker_data.data["electricity"]:
                        publish = True
                        worker_data.data["electricity"] = readings

                    worker_data.data["read_electricity"] = self.the_time_str()
                    worker_data.data["electricity_summary"] = self.pzem.to_abbr_str()
                    previous_pzem_read_time = time_ms()

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
