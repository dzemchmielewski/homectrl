import asyncio
import logging
import websockets
from websockets import ConnectionClosedError, WebSocketException


class PiWebSocket:
    def __init__(self, context: dict):
        self._context = context
        self._server = None
        if (up_self := context.get('self')) is not None:
            self._log = logging.getLogger(up_self.name + "-ws")
        else:
            self._log = logging.getLogger("ws")

    async def _handler(self, ws):
        try:
            async for data in ws:
                self._log.debug(f" >> {data}")
                try:
                    result = eval(data, self._context)
                except Exception as e:
                    result = f"Evaluating input error: {e}"
                self._log.debug(f" << {result}")
                await ws.send(str(result))
        except WebSocketException:
            pass

    async def start_server(self, host="0.0.0.0", port=8123, debug=False):
        self._log.info(f"START host:{host}, port: {port}, debug: {debug}")
        self._server = await websockets.serve(self._handler, host, port)

    def shutdown(self):
        self._log.info("SHUTDOWN")
        if self._server:
            self._server.close()


if __name__ == '__main__':
    class TestClass:
        def __init__(self):
            self.n = 0
        def inc(self):
            self.n += 1
    test = TestClass()

    pi_server = PiWebSocket(globals())

    async def main():
        await pi_server.start_server()
        await pi_server._server.wait_closed()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("EXIT")
        pi_server.shutdown()
