import time
from common.common import Common, CommonSerial, time_ms
from ld2410.ld2410 import LD2410
from modules.darkness_sensor import DarknessSensor

# TODO: Use boars.worker abstraction

class WorkerData:
    def __init__(self):
        self.is_alive = False
        self.go_exit = False
        self.loop_sleep = 1
        self.sensor_data = {
        }


worker_data = WorkerData()


class SwitchLightWorker(Common):

    def __init__(self, name, debug=True):
        super().__init__(name, debug)
        self.log("INIT")

        # LD2410 setup:
        self.detection_pin = 3
        self.gpio.setup_in(self.detection_pin)
        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=4, rx=5, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)

        # Photo-resistor:
        self.darkness = DarknessSensor("DARKNESS", 6, debug=debug)

        # Control light:
        self.light_pin = 2
        self.gpio.setup_out(self.light_pin)
        self.gpio.output(self.light_pin, self.gpio.input(self.detection_pin))


    def format_data(self, detection, input):
        if input[0][0] == 0:
            target_state = "  "
        elif input[0][0] == 1:
            target_state = " M"
        elif input[0][0] == 2:
            target_state = " S"
        elif input[0][0] == 3:
            target_state = "MS"
        else:
            target_state = " ?"

        return "[{}][{}][MOV: {:03}cm, {:03}%][STA: {:03}cm, {:03}%][DST: {:03}cm]".format("ON " if detection else "OFF", target_state,
                                                                                           *input[0][1:])

    def start(self):
        self.log("START")
        global worker_data
        worker_data.is_alive = True

        prev_detection = None
        prev_darkness = None
        current_light = None

        while not worker_data.go_exit:

            detection = self.gpio.input(self.detection_pin)
            # If there is a detection change:
            if detection != prev_detection:
                # let's make sure it is not just a fluctuation:
                time.sleep(0.5)
                detection = self.gpio.input(self.detection_pin)

                # if this is a pin change ON -> OFF:
                if prev_detection and not detection:
                    # let's wait another second(s):
                    time.sleep(1)
                    detection = self.gpio.input(self.detection_pin)

            # TODO: Complete the code
            # if
            #

            darkness = self.darkness.is_darkness()

            # Finally,
            # if the motion pin switch is confirmed
            if detection != prev_detection:
                # switch the light:
                self.gpio.output(self.detection_pin, detection)
                prev_detection = detection
                self.log("ON -> OFF" if not detection else "OFF -> ON")

            worker_data.sensor_data["detection"] = detection
            worker_data.sensor_data["radar"] = self.radar.get_radar_data()
            worker_data.sensor_data["darkness"] = self.darkness.is_darkness()
            self.log(self.format_data(detection, worker_data.sensor_data["radar"]))

            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")


if __name__ == '__main__':
    try:
        SwitchLightWorker("SwitchLight - TEST").start()
    except KeyboardInterrupt:
        pass

# exec(open("micro_python/switch_light_worker.py").read())
