from board.wardrobe_worker import WardrobeWorker
from board.worker import WorkerServer
from common.communication import SocketCommunication

try:
    worker = WardrobeWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    WorkerServer("WARDROBE_SRV", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass
