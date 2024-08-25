from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from storage import Live, Light, Radio

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


@router.get("/lights")
async def get_lights():
    result = [{
        "timestamp": obj.create_at,
        "name": obj.name_id,
        "value": obj.value
    }
        for obj in Light.get_currents()
    ]
    return {"status": "OK", "result": result}


@router.get("/radio")
async def get_radio():
    live = Live.get_last("radio")
    result = {"status": "OK"}
    radio = Radio.get_last()
    result["result"] = radio.__dict__['__data__'] if radio else {}
    result["result"]["is_alive"] = live.value if live else False
    return result


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
    uvicorn.run(app, host=bind_to, port=8000)
