import asyncio
import uuid

from starlette.websockets import WebSocketState, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from classy_fastapi import Routable, get, websocket
from fastapi import FastAPI, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager

from backend.storage import FigureCache, ChartPeriod
from common.common import Common
from configuration import Configuration, Topic
from backend.tools import json_serial, json_deserial, MQTTClient


class ConnectionManager(Common):

    def __init__(self) -> None:
        super().__init__("RESTAPI", debug=False)
        self.connections = {}
        self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
        self.onair = {}

    def on_start(self):
        self.mqtt.loop_start()
        self.log("ON START!!!")

    def on_stop(self):
        self.mqtt.disconnect()
        self.mqtt.loop_stop()
        self.log("ON STOP!!!")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
        client.subscribe(Topic.OnAir.format("+", "+"))

    def on_disconnect(self, *args, **kwargs):
        self.log("MQTT disconnected!")

    def on_message(self, client, userdata, msg):
        self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
        facet, device = Topic.OnAir.parse(msg.topic)
        message = json_deserial(msg.payload.decode())
        message["name"] = device
        if facet != "live":
            message["live"] = self.onair.get("live") and self.onair["live"].get(device) and self.onair["live"][device]["value"]
        if not self.onair.get(facet):
            self.onair[facet] = {}
        self.onair[facet][device] = message
        asyncio.run(self.send_message(self.prepare_response(facet), facet))

    def prepare_response(self, facet: str):
        return json_serial({"status": "OK", "result": list(self.onair[facet].values())})

    async def connect(self, ws: WebSocket, facet: str = None) -> str:
        await ws.accept()
        id = str(uuid.uuid4())
        self.debug("Client #{} connected".format(id))
        if not self.connections.get(facet):
            self.connections[facet] = {}
        self.connections[facet][id] = ws
        await ws.send_text(self.prepare_response(facet))
        return id

    async def disconnect(self, id, facet: str = None) -> None:
        self.debug("Client #{} removed from manager".format(id))
        del self.connections[facet][id]

    async def send_message(self, message, facet: str = None) -> None:
        # self.log("Send Message[{}]. Clients: {}".format(facet, self.connections))
        if self.connections.get(facet):
            for id, ws in self.connections[facet].items():
                try:
                    await ws.send_text(message)
                except ConnectionClosed:
                    self.debug("Client #{} disconnected while send".format(id))
                    await self.disconnect(id, facet)


class HomeCtrlAPI(Routable):

    def __init__(self) -> None:
        super().__init__(prefix='/homectrl/v1')
        self.connection_manager = ConnectionManager()

    async def ws_facet(self, ws: WebSocket, facet: str):
        id = await self.connection_manager.connect(ws, facet)
        try:
            while ws.application_state == WebSocketState.CONNECTED:
                data = await ws.receive_text()
                self.connection_manager.debug("Client {} recv data: {}".format(id, data))
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            self.connection_manager.debug("Client {} disconnected while recv".format(id))
            await self.connection_manager.disconnect(id, facet)
        self.connection_manager.debug("Client {} has gone".format(id))

    @websocket("/ws/humidity")
    async def humidity(self, ws: WebSocket):
        await self.ws_facet(ws, "humidity")

    @websocket("/ws/temperature")
    async def temperature(self, ws: WebSocket):
        await self.ws_facet(ws, "temperature")

    @websocket("/ws/pressure")
    async def pressure(self, ws: WebSocket):
        await self.ws_facet(ws, "pressure")

    @websocket("/ws/live")
    async def live(self, ws: WebSocket):
        await self.ws_facet(ws, "live")

    @websocket("/ws/light")
    async def light(self, ws: WebSocket):
        await self.ws_facet(ws, "light")

    @websocket("/ws/darkness")
    async def darkness(self, ws: WebSocket):
        await self.ws_facet(ws, "darkness")

    @websocket("/ws/presence")
    async def presence(self, ws: WebSocket):
        await self.ws_facet(ws, "presence")

    @websocket("/ws/radio")
    async def radio(self, ws: WebSocket):
        await self.ws_facet(ws, "radio")

    @websocket("/ws/voltage")
    async def voltage(self, ws: WebSocket):
        await self.ws_facet(ws, "voltage")

    @websocket("/ws/electricity")
    async def voltage(self, ws: WebSocket):
        await self.ws_facet(ws, "electricity")

    @websocket("/ws/activity")
    async def activity(self, ws: WebSocket):
        await self.ws_facet(ws, "activity")

    @get("/chart/{period}/{facet}/{device}")
    async def get_basic_chart(self, period: str, facet: str, device: str):
        cache = FigureCache.get_last(facet[0].upper() + facet[1:], ChartPeriod.from_str(period), device)
        if not cache:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        return Response(content=cache.getvalue(), media_type="image/png", status_code=status.HTTP_200_OK)

    @get("/dump")
    async def dump(self):
        return self.connection_manager.onair

    # @get("/pressure")
    # async def get_presence(self):
    #     return self._get_currents(Pressure)
    #
    # @get("/radio")
    # async def get_radio(self):
    #     live = Live.get_last("radio")
    #     result = {"status": "OK"}
    #     radio = Radio.get_last()
    #     result["result"] = radio.__dict__['__data__'] if radio else {}
    #     result["result"]["is_alive"] = live.value if live else False
    #     return result
    #
    #
    # def _get_currents(clazz):
    #     result = [{
    #         "timestamp": obj.create_at,
    #         "name": obj.name_id,
    #         "value": obj.value
    #     }
    #         for obj in clazz.get_currents()
    #     ]
    #     return {"status": "OK", "result": result}


api = HomeCtrlAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    api.connection_manager.on_start()
    yield
    api.connection_manager.on_stop()

app = FastAPI(lifespan=lifespan)

app.include_router(api.router)
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://192.168.0.21:3000",
    "http://192.168.0.21:80",
    "http://192.168.0.21",
    "http://status.home.arpa:3000",
    "http://status.home.arpa:80",
    "http://status.home.arpa",
    "http://status.home:3000",
    "http://status.home:80",
    "http://status.home",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":

    import uvicorn
    import socket

    if socket.gethostname() == 'pi2':
        bind_to = '192.168.0.21'
    else:
        bind_to = 'localhost'

    uvicorn.run("__main__:app", host=bind_to, port=8000, workers=1)

