from common_main import _blink

_blink()

from common.dummy_worker import DummyWorker
from common.communication import SerialCommunication, CommonSerial
from common.server import WorkerServer

try:
    worker = DummyWorker("DUMMY_WORKER")
    # connection = SocketCommunication("SOCKET", "", 8123, is_server=True)
    connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
    WorkerServer("WORKER_SERVER", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass

# exec(open("main.py").read())

