import asyncio
import importlib.util
import inspect
import pathlib

import logging
import threading
import traceback

from backend.storage import *
from backend.tools import MQTTClient
from backend.services.onairservice import OnAirService

logger = logging.getLogger("onair")
PLUGINS_DIR = pathlib.Path(__file__).parent / "services"

class OnAir:

    def __init__(self):
        self.mqtt = None
        self.loop = None
        self.stop_event = asyncio.Event()
        self.services = self._load_services()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        try:
            logger.info(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
            for service in self.services:
                service.on_connect(client, userdata, flags, reason_code, properties)
        except UnicodeError as e:
            logger.fatal("Unicode error caught! {}".format(e))
            traceback.print_exc()
        except Exception as e:
            logger.fatal("Exception caught! {}".format(e))
            traceback.print_exc()

    def on_message(self, client, userdata, msg):
        try:
            logger.debug(f"[{msg.topic}]{msg.payload.decode()}")
            for service in self.services:
                service.on_message(client, userdata, msg)
        except UnicodeError as e:
            logger.fatal("Unicode error caught! {}".format(e))
            logger.fatal("On message: [{}]{}".format(msg.topic, msg.payload))
            traceback.print_exc()
        except Exception as e:
            logger.fatal("Exception caught! {}".format(e))
            logger.fatal("On message: [{}]{}".format(msg.topic, msg.payload.decode()))
            traceback.print_exc()

    def on_disconnect(self, *args, **kwargs):
        try:
            logger.info("MQTT disconnected!")
            for service in self.services:
                service.on_disconnect(*args, **kwargs)
        except UnicodeError as e:
            logger.fatal("Unicode error caught! {}".format(e))
            traceback.print_exc()
        except Exception as e:
            logger.fatal("Exception caught! {}".format(e))
            traceback.print_exc()

    @staticmethod
    def _load_services():
        tasks = []
        for file in PLUGINS_DIR.glob("*.py"):
            spec = importlib.util.spec_from_file_location(file.stem, file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, OnAirService) and obj is not OnAirService:
                    tasks.append(obj())
        return tasks

    async def main(self):
        logger.info(f"OnAir services: {self.services}")
        self.loop = asyncio.get_running_loop()
        self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)

        for service in self.services:
            service.mqtt = self.mqtt

        thread = threading.Thread(target=self.mqtt.loop_forever, daemon=True)
        thread.start()

        tasks = [asyncio.create_task(p.run()) for p in self.services]

        await self.stop_event.wait()
        await asyncio.gather(*tasks, return_exceptions=True)

        self.mqtt.disconnect()
        self.mqtt.loop_stop()

        # Wait for MQTT thread to exit
        thread.join(timeout=2)

    def start(self):
        for service in self.services:
            service.on_start()
        asyncio.run(self.main())

    def stop(self):
        for service in self.services:
            service.on_stop()
        self.stop_event.set()

if __name__ == "__main__":
    OnAir().start()
