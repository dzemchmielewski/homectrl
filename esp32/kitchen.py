from board.worker import WorkerServer
from board.kitchen_worker import KitchenWorker
from common.communication import SocketCommunication

try:
    worker = KitchenWorker()
    connection = SocketCommunication("SOCKET", "", 8123, is_server=True, debug=False)
    # connection = SerialCommunication("SERIAL", CommonSerial(0, 76800, tx=0, rx=1, timeout=2), debug=False)
    WorkerServer("KITCHEN_SRV", communication=connection, worker=worker).start()
except KeyboardInterrupt:
    pass

# exec(open("launch.py").read())