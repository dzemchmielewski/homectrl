from board.worker import WorkerServer
from board.socket_worker import SocketWorker
from common.communication import SocketCommunication

try:
    worker = SocketWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    # connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
    WorkerServer("SOCKET", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass
