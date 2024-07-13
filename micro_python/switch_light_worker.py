from common.common import Common
import time
import random


class WorkerData:
    def __init__(self):
        self.is_alive = False
        self.go_exit = False
        self.loop_sleep = 1
        self.some_data = {
            "value": False
        }


worker_data = WorkerData()


class SwitchLightWorker(Common):

    def __init__(self, name, debug=True):
        super().__init__(name, debug)
        self.log("INIT")

    def start(self):
        self.log("START")
        global worker_data
        worker_data.is_alive = True

        while not worker_data.go_exit:
            # Some logic here:
            if random.randint(0, 9) > 7:
                value = not worker_data.some_data["value"]
                worker_data.some_data["value"] = value
                self.debug("ON -> OFF" if not value else "OFF -> ON")
                # TODO: switch output pin value

            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")


if __name__ == '__main__':
    try:
        SwitchLightWorker("SwitchLight - TEST").start()
    except KeyboardInterrupt:
        pass

# exec(open("micro_python/switch_light_worker.py").read())
