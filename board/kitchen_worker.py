from board.worker import Worker
from modules.darkness import DarknessSensor
from modules.dht import DHTSensor
import time
from common.common import time_ms


class KitchenWorker(Worker):

    def __init__(self, debug=True):
        super().__init__("KITCHEN", debug)
        self.log("INIT")
        self.dht_sensor = DHTSensor("DHT", 7)
        self.last_dht_read = None
        self.darkness_sensor = DarknessSensor("DARKNESS", 9)



    def start(self):
        self.log("START")
        worker_data = self.get_data()
        worker_data.is_alive = True
        worker_data.data["name"] = self.name

        while not worker_data.go_exit:

            # DHT sensor:
            if self.last_dht_read is None or time_ms() - self.last_dht_read > 60:
                temp, hum = self.dht_sensor.get()
                worker_data.data["temperature"] = temp
                worker_data.data["humidity"] = hum
                worker_data.data["dht_time"] = time.localtime()
                self.last_dht_read = time_ms()

            # Darkness sensor:
            worker_data.data["darkness"] = self.darkness_sensor.is_darkness()

            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")

