from board.worker import WorkerServer
from desk_worker import DeskWorker
from common.communication import SocketCommunication

try:
    worker = DeskWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    # connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
    WorkerServer("DESK_SRV", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass
