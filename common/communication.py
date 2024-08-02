from common.common import Common, CommonSerial
import time

try:
    import socket
except ImportError:
    print("Cannot import socket!")


class Communication(Common):

    def __init__(self, name: str, debug=False):
        super().__init__(name, debug)

    def send(self, message) -> None:
        pass

    def receive(self) -> str:
        pass

    def send_bytes(self, message_bytes: bytes):
        pass

    def receive_bytes(self, size) -> bytes:
        pass

    def close(self) -> None:
        pass

    def __str__(self):
        return "COM None"


class SerialCommunication(Communication):

    def __init__(self, name: str, serial: CommonSerial, debug=False):
        super().__init__(name, debug)
        self.serial = serial

    def send(self, message) -> None:
        self.debug("Sending message: {}".format(message))
        if not message.endswith("\n"):
            message += "\n"
        self.serial.write("{}".format(message).encode())
        self.serial.flush()

    def receive(self) -> str:
        self.debug("Receiving message...")
        while not (data := self.serial.readline()):
            pass
        data = data.decode()
        data = data.strip()
        self.debug("Received message: {}".format(data))
        return  data

    def send_bytes(self, message_bytes: bytes) -> None:
        self.debug("Sending bytes; size: {}".format(len(message_bytes)))
        self.serial.write(message_bytes)
        self.serial.flush()

    def receive_bytes(self, size) -> bytes:
        self.debug("Receiving bytes; size={}".format(size))
        data = self.serial.read(size)
        self.debug("Received bytes; size={}".format(len(data)))
        return data

    def __str__(self):
        return "COM {}".format(self.serial)


class SocketCommunication(Communication):

    def __init__(self, name: str, host: str, port: int, is_server: bool = False, read_timeout: int = 3*60, debug=False):
        super().__init__(name, debug)
        self.host = host
        self.port = port
        self.is_server = is_server
        self.socket = None
        self.comm_channel = None
        self.read_timeout = read_timeout

    def __str__(self):
        return "COM Socket: {}:{}".format("0.0.0.0" if self.host is None or self.host == '' else self.host, self.port)

    def __del__(self):
        # print("Deleting socket")
        self.close(on_unload=True)

    def send(self, message):
        if self.comm_channel is None:
            self._init()
        self.debug("Sending message: {}".format(message))
        if not message.endswith("\n"):
            message += "\n"
        self.comm_channel.send(message.encode())

    def receive(self) -> str:
        self.debug("Receiving message...")
        if self.comm_channel is None:
            self._init()
        data = ""
        while not data.endswith("\n"):
            data += self.comm_channel.recv(1024).decode()
        data = data.strip()
        self.debug("Received message: {}".format(data))
        return data

    def send_bytes(self, message_bytes: bytes):
        self.debug("Sending bytes; size: {}".format(len(message_bytes)))
        if self.comm_channel is None:
            self._init()
        self.comm_channel.send(message_bytes)

    def receive_bytes(self, size) -> bytes:
        self.debug("Receiving bytes...")
        if self.comm_channel is None:
            self._init()
        data = bytearray()
        while len(data) < size:
            packet = self.comm_channel.recv(size - len(data))
            data.extend(packet)
            self.debug("Received bytes; size={}, total={}".format(len(packet), len(data)))
        self.debug("Received bytes completed; total={}".format(len(data)))
        return data

    def close(self, on_unload = False) -> None:
        if self.comm_channel is not None:
            if not on_unload:
                self.debug("Closing connection")
            self.comm_channel.close()
            self.comm_channel = None
        else:
            if not on_unload:
                self.debug("Closing socket")
            # self.socket.shutdown(socket.SHUT_RDWR)
            if self.socket is not None:
                self.socket.close()
                self.socket = None

    def _init(self) -> bool:
        if self.is_server:
            return self._init_server()
        else:
            return self._init_client()

    def _init_server(self):
        if self.socket is None:
            self.debug("Socket bind and listen")
            self.socket = socket.socket()
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen()

        self.debug("Waiting for client")
        c, addr = self.socket.accept()
        self.debug("Connection from: {}".format(addr))

        self.comm_channel = c
        self.comm_channel.settimeout(self.read_timeout)
        # read Hello from client:
        hello = self.receive()

        # TODO: allowed IPs
        if hello.upper().strip() != "HELLO":
            self.send("Sorry")
            self.comm_channel.close()
            self.comm_channel = None
            return False

        self.send("Hello from server.")
        self.debug("Accepted connection from: {}".format(addr))
        return True

    def _init_client(self):
        self.debug("Initialize client connection")
        self.socket = socket.socket()
        successfully_connected = False
        attempts = 0

        last_error = None
        while not successfully_connected and attempts < 5:
            try:
                self.socket.connect((self.host, self.port))

                successfully_connected = True
            except OSError as e:
                time.sleep(0.3)
                attempts += 1
                last_error = e

        if not successfully_connected:
            raise OSError("Connection not established after {} attempts. Last error: {}".format(attempts, last_error))

        self.comm_channel = self.socket

        self.send("Hello")
        response = self.receive()
        self.debug("Connected: {}".format(response))


