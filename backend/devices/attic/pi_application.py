import asyncio
import datetime
import json
import signal
import threading
import time
import logging

from backend.devices.attic.pi_web_socket import PiWebSocket
from configuration import Configuration, Topic
from backend.tools import MQTTClient, json_serial

time_str_s = lambda s: datetime.datetime.fromtimestamp(int(s)).strftime('%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("pi_application")

class Facility:
    def __init__(self, name, endpoint = None, value=None, to_dict=None, register_set=True, register_access=True):
        self.name = name
        self._endpoint = endpoint
        self._to_dict = to_dict if to_dict else (lambda x: {x.name: x.value})
        self._value = value
        self.register_set = register_set
        self.set = None
        self.register_access = register_access
        self.access = None
        self.task = None
        self.event = asyncio.Event()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.register_set:
            self.set = time.time()
        self._value = value

    @property
    def endpoint(self):
        if self.register_access:
            self.access = time.time()
        return self._endpoint

    def to_dict(self):
        return ({self.name + "_time":
                     ({"set": time_str_s(self.set)} if self.set else {})
                     | ({"access": time_str_s(self.access)} if self.access else {})
                 }
                | self._to_dict(self))

    def __iter__(self):
        return iter(self.to_dict().items())


class PiApplication:

    def __init__(self, name: str, use_mqtt: bool = True):
        self.start_time = time.time()
        self.name = name

        self.exit = False
        self.loop = None
        self.ws_server = PiWebSocket({'self': self} | globals())
        self.use_mqtt = use_mqtt
        if self.use_mqtt:
            self.mqtt = None
            self.topic_live, self.topic_state, self.topic_capabilities, topic_control = (
                Topic.Device.format(name, Topic.Device.Facility.live),
                Topic.Device.format(name, Topic.Device.Facility.state),
                Topic.Device.format(name, Topic.Device.Facility.capabilities),
                Topic.Device.format(name, Topic.Device.Facility.control))
            self.mqtt_subscriptions = {topic_control: None}

        self.control = {}
        self.capabilities = {'controls': []}

    def info(self):
        return json.dumps({'todo': 'TODO'})

    async def publish(self, topic, data, retain=False, qos=0, properties=None):
        if self.use_mqtt:
            self.mqtt.publish(topic, json_serial(data), qos=qos, retain=retain, properties=properties)

    async def start(self):
        pass

    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.debug(f"mqtt on connect (topic live: {self.topic_live})")
        asyncio.run_coroutine_threadsafe(
            self.publish(self.topic_live, {'live': True}, retain=True), self.loop)

    def on_message(self, client, userdata, msg):
        pass

    def on_disconnect(self, *args, **kwargs):
        logger.debug("mqtt on disconnect")
        asyncio.run_coroutine_threadsafe(
            self.publish(self.topic_live, {'live': False}, retain=True), self.loop)

    def on_start(self):
        logger.debug("mqtt on start")

    def on_stop(self):
        logger.debug("mqtt on stop")

    async def _asyncio_entry(self):
        logger.debug("ASYNC entry")
        self.loop = asyncio.get_running_loop()

        if self.use_mqtt:
            self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
            thread = threading.Thread(target=self.mqtt.loop_forever, daemon=True)
            thread.start()

        asyncio.create_task(self.start())
        asyncio.create_task(self.ws_server.start_server())

        self._stop_event = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, self._stop_event.set)

        await self._stop_event.wait()

        logger.debug("ASYNC exit")
        if self.use_mqtt:
            logger.debug("mqtt exit")
            await self.publish(self.topic_live, {'live': False}, retain=True)
            self.mqtt.disconnect()
            self.mqtt.loop_stop()

            # Wait for MQTT thread to exit
            thread.join(timeout=2)


    def go_exit(self):
        self.exit = True
        if self.loop and hasattr(self, '_stop_event'):
            self.loop.call_soon_threadsafe(self._stop_event.set)

    def deinit(self):
        self.ws_server.shutdown()
        if self.use_mqtt:
            self._mqtt_messages_task.cancel()

    def run(self):
        try:
            asyncio.run(self._asyncio_entry())
        finally:
            self.exit = True
            logger.info("END")

    @staticmethod
    def validate_controls(capabilities, input: dict) -> dict:
        result = {}
        if capabilities := capabilities:

            for control in capabilities["controls"]:
                name = control["name"]
                if name in input:
                    value = input[name]

                    # Check type using eval on control_type
                    if not isinstance(value, eval(control["type"])):
                        continue  # Invalid type, skip this entry

                    constraints = control.get("constraints")
                    if isinstance(constraints, dict) and constraints:

                        # Validate constraints
                        if constraints["type"] == "enum":
                            if value in constraints["values"]:
                                result[name] = value  # Valid enum value

                        elif constraints["type"] == "range":
                            if constraints["values"]["min"] <= value <= constraints["values"]["max"]:
                                result[name] = value  # Valid range value
                    else:
                        result[name] = value  # No constraints, accept the value

        return result

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

    class DummyApplication(PiApplication):
        def __init__(self):
            super().__init__('dummy')
            self.n = 0

        async def work1(self):
            while not self.exit:
                logger.info(f"N: {self.n}")
                self.n += 1
                await asyncio.sleep(2)


        async def start(self):
            logger.info("DUMMY START")
            asyncio.create_task(self.work1())


    DummyApplication().run()
