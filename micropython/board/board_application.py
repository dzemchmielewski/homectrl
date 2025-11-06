import asyncio
import time
import os

import board.board_shared as shared
from board.board_shared import Utils as util
from board.board_web_socket import BoardWebSocket
from board.mqtt_as import MQTTClient
from board.mqtt_as import config as mqttconfig
from configuration import Configuration

from board.boot import Boot
import json, machine, esp32, gc, ubinascii

class MQTT(shared.Exitable, shared.Named):

    I_AM_ALIVE = json.dumps({"live": True, 'message': 'hello'})
    LAST_WILL = json.dumps({"live": False, 'message': "last will"})
    END_OF_LIVE = json.dumps({"live": False, 'message': "goodbye"})

    def __init__(self, app_name, subscriptions={}):
        shared.Exitable.__init__(self)
        shared.Named.__init__(self, 'mqtt')
        self.subscriptions = subscriptions
        (self.topic_live, _, _, _, _) = Configuration.topics(app_name)
        mqttconfig['server'] = Configuration.MQTT_SERVER
        mqttconfig['user'] = Configuration.MQTT_USERNAME
        mqttconfig['password'] = Configuration.MQTT_PASSWORD
        mqttconfig['port'] = 1883
        mqttconfig['queue_len'] = 1
        mqttconfig['ssid'] = Configuration.WIFI_SSID
        mqttconfig['wifi_pw'] = Configuration.WIFI_PASSWORD
        mqttconfig["will"] = (self.topic_live, MQTT.LAST_WILL, True, 0)
        mqttconfig["iftype"] = Boot.get_instance().iftype()
        mqttconfig["ifnetwork"] = Boot.get_instance().ifnetwork()

        self.is_initially_connected = False

        MQTTClient.DEBUG = False
        self.client = MQTTClient(mqttconfig)
        self._up_task = asyncio.create_task(self.on_up())

    async def connect(self):
        try:
            await self.client.connect()
            self.is_initially_connected = True
        except OSError as e:
            self.log.error(f"MQTT connecting FAILED")
            self.log.exception(e)

    async def on_up(self):
        while not self.exit:
            await self.client.up.wait()
            self.client.up.clear()
            self.log.info("MQTT connection established")
            await self.client.publish(self.topic_live, self.I_AM_ALIVE, True)
            for topic in self.subscriptions.keys():
                await self.client.subscribe(topic)
                self.log.info(f"MQTT listen to topic: {topic}")

    async def publish(self, topic, data, retain=False, qos=0, properties=None):
        if not self.is_initially_connected:
            await self.connect()
        if self.is_initially_connected:
            try:
                await self.client.publish(topic, data, retain, qos, properties)
            except OSError as e:
                self.log.error(f"MQTT publish FAILED - topic: '{topic}', message: '{data}', error: {e}")
        else:
            self.log.error(f"MQTT publish FAILED - not connected - topic: '{topic}', message: '{data}'")

    def deinit(self):
        self.client.publish(self.topic_live, self.END_OF_LIVE, True)
        super().deinit()
        self._up_task.cancel()
        self.client.disconnect()

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

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.register_set:
            self.set = time.time_ms()
        self._value = value

    @property
    def endpoint(self):
        if self.register_access:
            self.access = time.time_ms()
        return self._endpoint

    def to_dict(self):
        return ({self.name + "_time":
            ({"set": util.time_str_ms(self.set)} if self.set else {})
            | ({"access": util.time_str_ms(self.access)} if self.access else {})
        }
        | self._to_dict(self))

    def __iter__(self):
        return iter(self.to_dict().items())


class BoardApplication(shared.Named, shared.Exitable):

    def __init__(self, name: str, use_mqtt: bool = True):
        shared.Exit.init()
        if not hasattr(self, 'name'):
            shared.Named.__init__(self, name)
        shared.Exitable.__init__(self)
        self.start_time = time.time_ms()
        self.time_sync = Facility("time_sync", Boot.get_instance(), 0,
                                  lambda x: {'time': {'now': util.time_str(), 'sync_index': x.value, 'sync_time': util.time_str_ms(x.set)}})
        self.ws_server = BoardWebSocket({'self': self} | globals())
        self.use_mqtt = use_mqtt
        if self.use_mqtt:
            self.mqtt = None
            (self.topic_live, _, self.topic_state, self.topic_capabilities, topic_control) = Configuration.topics(name)
            self.mqtt_subscriptions = {topic_control: None}

        self.control = {}
        self.capabilities = {'controls': []}

    def info(self):
        boot = Boot.get_instance()
        return json.dumps({
            'machine': {
                'id': ubinascii.hexlify(machine.unique_id()).decode(),
                'frequency': machine.freq() / 1_000_000,
                'mcu_temperature': esp32.mcu_temperature() if hasattr(esp32,'mcu_temperature') else None,
            },
            'os': {
                'uname': {key: eval('os.uname().' + key) for key in dir(os.uname()) if not key.startswith('__')},
                'uptime': util.format_uptime((time.time_ms() - boot.load_time) // 1_000),
            },
            'mem': {
                'alloc': gc.mem_alloc(),
                'free': gc.mem_free(),
            },
            'app_up_time': util.format_uptime((time.time_ms() - self.start_time) // 1_000),
            'boot': {
                'version': boot.version,
                'load_time': util.time_str_ms(boot.load_time),
                'loaded': boot.loaded,
            },
            'network': {
                'iftype': boot.iftype(),
                'ifconfig': boot.ifconfig(),
            }
        } | self.time_sync.to_dict())

    async def publish(self, topic, data, retain=False, qos=0, properties=None):
        if self.use_mqtt:
            await self.mqtt.publish(topic, json.dumps(data), retain, qos, properties)

    async def start(self):
        if self.use_mqtt:
            self.mqtt = MQTT(self.name, self.mqtt_subscriptions)
            await self.mqtt.connect()
            # await self.publish(self.topic_state, self.control, True)
            # await self.publish(self.topic_capabilities, self.capabilities, True)

    async def mqtt_messages(self):
        async for topic, msg, retained in self.mqtt.client.queue:
            themessage = msg.decode()
            thetopic = topic.decode()
            self.log.info(f"MQTT incoming - topic: '{thetopic}', message: '{themessage}', retained: {retained}")
            if thetopic in self.mqtt.subscriptions and (callback := self.mqtt.subscriptions[thetopic]) is not None:
                callback(thetopic, themessage, retained)
            else:
                try:
                    controls = json.loads(themessage)
                    for key, value in self.validate_controls(self.capabilities, controls).items():
                        self.control[key] = value
                    await self.publish(self.topic_state, self.control, True)
                except Exception as e:
                    await self.publish(self.topic_live,
                                 {"live": True, 'error': f"Incoming MQTT message problem: {themessage}, error: {e}"}, False)

    async def daily_rtc_sync(self):
        while not self.exit:
            now = time.localtime()
            h, m, s = now[3], now[4], now[5]
            seconds_today = h * 60 * 60 + m * 60 + s

            # Seconds until next 03:30
            target = 3 * 60 * 60 + 30 * 60
            if seconds_today < target:
                wait = target - seconds_today
            else:
                wait = 24 * 60 * 60 - seconds_today + target

            await asyncio.sleep(wait)

            self.log.info(f"Daily RTC sync task started. Date/Time: {util.time_str()}")
            try:
                if self.time_sync.endpoint.setup_time():
                    # Just a dummy increment to indicate that sync was done
                    self.time_sync.value = self.time_sync.value + 1
                    self.log.info(f"Daily RTC sync finished successfully. Date/Time: {util.time_str()}")
                else:
                    self.log.info(f"Daily RTC sync not completed.")
            except Exception as e:
                self.log.error(f"Daily RTC sync failed: {e}")


    async def _asyncio_entry(self):
        asyncio.create_task(self.start())
        if self.use_mqtt:
            self._mqtt_messages_task = asyncio.create_task(self.mqtt_messages())
        self.time_sync.task = asyncio.create_task(self.daily_rtc_sync())
        asyncio.create_task(self.ws_server.start_server())
        while not shared.Exit.is_exit():
            await asyncio.sleep(1)

    def go_exit(self):
        shared.Exit.go()

    def deinit(self):
        self.ws_server.shutdown()
        if self.use_mqtt:
            self._mqtt_messages_task.cancel()
        self.time_sync.task.cancel()

    def run(self):
        async def nothing():
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                pass
        try:
            asyncio.run(self._asyncio_entry())
        except KeyboardInterrupt:
            self.log.info("SIGINT")
        finally:
            shared.Exit.go()
            asyncio.get_event_loop().run_until_complete(nothing())
            self.log.info("END")

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

# if __name__ == "__main__":
#
#     class DummyApplication(BoardApplication):
#         def __init__(self):
#             super().__init__('dummy')
#             self.n = 0
#
#         async def work1(self):
#             while not config.EXIT:
#                 logging.info(f"N: {self.n}")
#                 self.n += 1
#                 await asyncio.sleep_ms(20_000)
#
#
#         async def start(self):
#             logging.info("DUMMY START")
#             asyncio.create_task(self.work1())
#
#
#     DummyApplication().run()
