from fastapi import APIRouter, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from storage import Live, Light, Radio, Darkness, Presence, Pressure, Humidity, Temperature, FigureCache

router = APIRouter(prefix='/homectrl/v1')

def log(msg):
    print("--------> {}".format(msg))


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/live")
async def get_live():
    result = [{
        "timestamp": obj.create_at,
        "name": obj.name_id,
        "is_alive": obj.value
        }
        for obj in Live.get_currents()
    ]
    return {"status": "OK", "result": result}


@router.get("/light")
async def get_light():
    return _get_currents(Light)


@router.get("/darkness")
async def get_darkness():
    return _get_currents(Darkness)


@router.get("/chart/{model}/{name}")
async def get_basic_chart(model: str, name: str):
    cache = FigureCache.get_last(model[0].upper() + model[1:], name)
    if not cache:
        return Response(status_code = status.HTTP_404_NOT_FOUND)
    return Response(content=cache.getvalue(), media_type="image/png", status_code=status.HTTP_200_OK)


@router.get("/presence")
async def get_presence():
    return _get_currents(Presence)


@router.get("/temperature")
async def get_presence():
    return _get_currents(Temperature)


@router.get("/humidity")
async def get_presence():
    return _get_currents(Humidity)


@router.get("/pressure")
async def get_presence():
    return _get_currents(Pressure)


@router.get("/radio")
async def get_radio():
    live = Live.get_last("radio")
    result = {"status": "OK"}
    radio = Radio.get_last()
    result["result"] = radio.__dict__['__data__'] if radio else {}
    result["result"]["is_alive"] = live.value if live else False
    return result


def _get_currents(clazz):
    result = [{
        "timestamp": obj.create_at,
        "name": obj.name_id,
        "value": obj.value
    }
        for obj in clazz.get_currents()
    ]
    return {"status": "OK", "result": result}



app = FastAPI()
app.include_router(router)
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

if __name__ == '__main__':
    import uvicorn
    import socket
    if socket.gethostname() == 'pi2':
        bind_to = '192.168.0.21'
    else:
        bind_to = 'localhost'
    uvicorn.run("__main__:app", host=bind_to, port=8000, workers=3)
    # uvicorn.run("__main__:app", host=bind_to, port=8000)
