import _thread
import json

from machine import UART, Pin

from micro_python.common_server import CommonServer
import micro_python.switch_light_worker as worker


class WorkerServer(CommonServer):

    def __init__(self, name, worker=None):
        super().__init__(name, 0, 1)
        self.worker = worker

    def handle_help(self):
        return "PIN switch server commands: dev, todo"

    def handle_message(self, msg):
        cmd = msg.strip().upper()

        if cmd == "GO":
            if worker.worker_data.is_alive:
                answer = "already started..."
            else:
                worker.worker_data.go_exit = False
                _thread.start_new_thread(self.worker.start, ())
                answer = "call worker {} start".format(self.worker)

        elif cmd == "NOGO":
            if worker.worker_data.is_alive:
                worker.worker_data.go_exit = True
                answer = "call worker exit"
            else:
                answer = "not alive..."

        elif cmd == "INFO":
            answer = json.dumps(worker.worker_data.__dict__)

        elif cmd == "DEV":
            try:
                from machine import UART, Pin
                from ld2410.ld2410 import LD2410
                uart = UART(1, baudrate=256000, bits=8, parity=None, stop=1, tx=Pin(4), rx=Pin(5), timeout=1)
                radar = LD2410("LD2410", uart)
                answer = radar.get_radar_data()
            except BaseException as e:
                answer = str(e)
        else:
            answer = "unknown command: {}".format(msg)

        return answer


if __name__ == '__main__':
    from micro_python.switch_light_worker import SwitchLightWorker
    try:
        switch_worker = SwitchLightWorker("WORKER switch light")
        WorkerServer("SERVER switch light", switch_worker).start()
    except KeyboardInterrupt:
        pass

# exec(open("micro_python/worker_server.py").read())