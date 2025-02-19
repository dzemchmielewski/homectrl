import asyncio
from board.microdot import Microdot
from board.microdot.websocket import with_websocket
import logging

class BoardWebSocket:
    microdot = Microdot()
    context = {}
    log = None

    def __init__(self, context: dict):
        BoardWebSocket.context = context
        if (up_self := context.get('self')) is not None:
            BoardWebSocket.log = logging.getLogger(up_self.name + "-ws")
        else:
            BoardWebSocket.log = logging.getLogger("ws")

    async def start_server(self, host="0.0.0.0", port=8123, debug=False):
        self.log.info(f"START host:{host}, port: {port}, debug: {debug}")
        await self.microdot.start_server(host=host, port=port, debug=debug)

    def shutdown(self):
        self.log.info("SHUTDOWN")
        self.microdot.shutdown()

    @microdot.route('')
    @with_websocket
    async def serve(request, ws):
        while True:
            data = await ws.receive()
            BoardWebSocket.log.debug(f" >> {data}")
            try:
                result = eval(data, BoardWebSocket.context)
            except Exception as e:
                result = f"Evaluating input error: {e}"
            BoardWebSocket.log.debug(f" << {result}")
            await ws.send(f"{result}")


if __name__ == '__main__':
    class TestClass:
        def __init__(self):
            self. n = 0
        def inc(self):
            self.n += 1
    test = TestClass()

    board_server = BoardWebSocket(globals())
    try:
        asyncio.run(board_server.start_server())
    except KeyboardInterrupt:
        print("EXIT")
        board_server.shutdown()
