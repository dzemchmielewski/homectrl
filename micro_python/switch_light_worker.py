import time
from common.common import Common, CommonSerial, time_ms
from ld2410.ld2410 import LD2410
from modules.darkness_sensor import DarknessSensor


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
        self.light_pin = 2

        # LD2410 setup:
        self.motion_pin = 3
        self.gpio.setup_in(self.motion_pin)
        self.gpio.setup_out(self.light_pin)
        self.gpio.output(self.light_pin, self.gpio.input(self.motion_pin))
        uart = CommonSerial(1, baudrate=256000, bits=8, parity=None, stop=1, tx=4, rx=5, timeout=1)
        self.radar = LD2410("LD2410", uart, debug=False)

        #Photoresistor:
        self.darkness = DarknessSensor("DARKNESS", 6, debug=debug)


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
        prev = None

        while not worker_data.go_exit:

            value = self.gpio.input(self.motion_pin)

            # If there is a pin state change:
            if value != prev:
                # let's make sure it is not just a fluctuation:
                time.sleep(0.2)
                value = self.gpio.input(self.motion_pin)

                # if this is a pin change ON -> OFF:
                if prev and not value:
                    # let's wait another second(s):
                    time.sleep(1)
                    value = self.gpio.input(self.motion_pin)

            #Finally, if the motion pin switch is confirmed
            if value != prev:
                # switch the light:
                self.gpio.output(self.motion_pin, value)
                prev = value
                self.log("ON -> OFF" if not value else "OFF -> ON")

            worker_data.sensor_data["detection"] = value
            worker_data.sensor_data["radar"] = self.radar.get_radar_data()
            worker_data.sensor_data["darkness"] = self.darkness.is_darkness()
            self.log(self.format_data(value, worker_data.sensor_data["radar"]))

            time.sleep(worker_data.loop_sleep)

        worker_data.is_alive = False
        self.log("EXIT")


if __name__ == '__main__':
    try:
        SwitchLightWorker("SwitchLight - TEST").start()
    except KeyboardInterrupt:
        pass

# exec(open("micro_python/switch_light_worker.py").read())
