from board.bathroom_worker import BathroomWorker
from board.worker import WorkerServer
from common.communication import SocketCommunication

try:
    worker = BathroomWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    WorkerServer("BATHROOM_SRV", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass

