from board.worker import Worker
from modules.dht import DHTSensor
import time


class KitchenWorker(Worker):

    def __init__(self, debug=True):
        super().__init__("KITCHEN", debug)
        self.log("INIT")
        self.dht_sensor = DHTSensor("DHT", 7)

    def start(self):
        self.log("START")
        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        while not worker_data.go_exit:

            # DHT sensor:
            temp, hum = self.dht_sensor.get()
            worker_data.data["temperature"] = temp
            worker_data.data["humidity"] = hum

            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")

