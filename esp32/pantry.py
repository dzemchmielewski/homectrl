from board.pantry_worker import PantryWorker
from board.worker import WorkerServer
from common.communication import SocketCommunication

try:
    worker = PantryWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    WorkerServer("PANTRY_SRV", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass

