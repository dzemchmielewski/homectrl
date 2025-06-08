import asyncio

import logging
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

    def __init__(self, app_name):
        shared.Exitable.__init__(self)
        shared.Named.__init__(self, 'mqtt')
        (self.topic_live, _, _, _, self.topic_control) = Configuration.topics(app_name)
        mqttconfig['server'] = Configuration.MQTT_SERVER
        mqttconfig['user'] = Configuration.MQTT_USERNAME
        mqttconfig['password'] = Configuration.MQTT_PASSWORD
        mqttconfig['port'] = 1883
        mqttconfig['queue_len'] = 1
        mqttconfig['ssid'] = Configuration.WIFI_SSID
        mqttconfig['wifi_pw'] = Configuration.WIFI_PASSWORD
        mqttconfig["will"] = (self.topic_live, MQTT.LAST_WILL, True, 0)

        MQTTClient.DEBUG = False
        self.client = MQTTClient(mqttconfig)
        self._up_task = asyncio.create_task(self.on_up())

    async def connect(self):
        try:
            await self.client.connect()
        except OSError as e:
            self.log.error(f"MQTT connecting FAILED")
            self.log.exception(e)

    async def on_up(self):
        while not self.exit:
            await self.client.up.wait()
            self.client.up.clear()
            self.log.info("MQTT connection established")
            await self.client.publish(self.topic_live, self.I_AM_ALIVE, True)
            await self.client.subscribe(self.topic_control)
            self.log.info(f"MQTT listen to topic: {self.topic_control}")

    def deinit(self):
        self.client.publish(self.topic_live, self.END_OF_LIVE, True)
        super().deinit()
        self._up_task.cancel()
        self.client.disconnect()


class BoardApplication(shared.Named, shared.Exitable):

    def __init__(self, name: str, use_mqtt: bool = True):
        shared.Exit.init()
        if not hasattr(self, 'name'):
            shared.Named.__init__(self, name)
        shared.Exitable.__init__(self)
        self.start_time = time.ticks_ms()
        self.ws_server = BoardWebSocket({'self': self} | globals())
        self.use_mqtt = use_mqtt
        if self.use_mqtt:
            self.mqtt = None
            (self.topic_live, _, self.topic_state, self.topic_capabilities, _) = Configuration.topics(name)
        self.control = {}
        self.capabilities = {'controls': []}

    def info(self):
        return json.dumps({
             'id': ubinascii.hexlify(machine.unique_id()).decode(),
            'uname': {key: eval('os.uname().' + key) for key in dir(os.uname()) if not key.startswith('__')},
            'frequency': machine.freq() / 1_000_000,
            'os_up_time': util.format_uptime(time.ticks_ms() // 1_000),
            'app_up_time': util.format_uptime((time.ticks_ms() - self.start_time) // 1_000),
            'mcu_temperature': esp32.mcu_temperature() if hasattr(esp32,'mcu_temperature') else None,
            'mem_alloc': gc.mem_alloc(),
            'mem_free': gc.mem_free(),
            'boot': Boot.get_instance().version,
            'ifconfig': Boot.get_instance().wifi.ifconfig(),
            'time': util.time_str()
        })

    async def publish(self, topic, data, retain=False, qos=0, properties=None):
        if self.use_mqtt:
            await self.mqtt.client.publish(topic, json.dumps(data), retain, qos, properties)

    async def start(self):
        if self.use_mqtt:
            self.mqtt = MQTT(self.name)
            await self.mqtt.connect()
            await self.publish(self.topic_state, self.control, True)
            await self.publish(self.topic_capabilities, self.capabilities, True)

    async def mqtt_messages(self):
        async for topic, msg, retained in self.mqtt.client.queue:
            message = msg.decode()
            self.log.info(f"MQTT incoming - topic: '{topic.decode()}', message: '{message}', retained: {retained}")
            try:
                controls = json.loads(message)
                for key, value in self.validate_controls(self.capabilities, controls).items():
                    self.control[key] = value
                await self.publish(self.topic_state, self.control, True)
            except Exception as e:
                await self.publish(self.topic_live,
                             {"live": True, 'error': f"Incoming MQTT message problem: {message}, error: {e}"}, False)

    async def _asyncio_entry(self):
        asyncio.create_task(self.start())
        if self.use_mqtt:
            self._mqtt_messages_task = asyncio.create_task(self.mqtt_messages())
        asyncio.create_task(self.ws_server.start_server())
        while not shared.Exit.is_exit():
            await asyncio.sleep(1)

    def go_exit(self):
        shared.Exit.go()

    def deinit(self):
        self.ws_server.shutdown()
        if self.use_mqtt:
            self._mqtt_messages_task.cancel()

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
                constraints = control["constraints"]

                if name in input:
                    value = input[name]

                    # Check type using eval on control_type
                    if not isinstance(value, eval(control["type"])):
                        continue  # Invalid type, skip this entry

                    # Validate constraints
                    if constraints["type"] == "enum":
                        if value in constraints["values"]:
                            result[name] = value  # Valid enum value

                    elif constraints["type"] == "range":
                        if constraints["values"]["min"] <= value <= constraints["values"]["max"]:
                            result[name] = value  # Valid range value

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
