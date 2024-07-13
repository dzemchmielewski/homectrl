import machine
import utime
from micro_python.switch_light_worker import SwitchLightWorker
from micro_python.worker_server import WorkerServer


def _blink(pattern):
    led_pin = machine.Pin(25, machine.Pin.OUT)
    for s in pattern:
        led_pin.value(1)
        utime.sleep(s)
        led_pin.value(0)
        utime.sleep(s)


_blink([0.5, 0.3, 0.2, 0.2, 0.1, 0.1, 0.1, 0.05, 0.05])


switch_worker = SwitchLightWorker("WORKER switch light")
WorkerServer("SERVER switch light", switch_worker).start()

# exec(open("main.py").read())
