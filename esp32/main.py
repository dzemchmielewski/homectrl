from board.worker import Worker, WorkerServer
from common.communication import SocketCommunication

try:
    worker = Worker("DUMMY_WORKER")
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    # connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
    WorkerServer("WORKER_SERVER", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass

# exec(open("main.py").read())