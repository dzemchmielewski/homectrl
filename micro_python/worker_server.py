import _thread
import json

from micro_python.common_server import CommonServer
import micro_python.switch_light_worker as worker


class WorkerServer(CommonServer):

    def __init__(self, name, worker=None):
        super().__init__(name, 0, 1)
        self.worker = worker

    def handle_help(self):
        return "WORKER SERVER COMMANDS: go, nogo, info, read"

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

        elif cmd == "READ":
            try:
                answer = json.dumps(worker.worker_data.sensor_data)
            except Exception as e:
                answer = str(e)

        return answer


if __name__ == '__main__':
    from micro_python.switch_light_worker import SwitchLightWorker
    try:
        switch_worker = SwitchLightWorker("WORKER switch light")
        WorkerServer("SERVER switch light", switch_worker).start()
    except KeyboardInterrupt:
        pass

# exec(open("micro_python/worker_server.py").read())
