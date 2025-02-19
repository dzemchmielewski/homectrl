import asyncio
import time
import os

import board.board_shared as shared
from board.board_web_socket import BoardWebSocket
from board.mqtt_as import MQTTClient

from board.boot import Boot
import json, machine, esp32, gc, ubinascii

class MQTT:

    I_AM_ALIVE = json.dumps({"live": True, 'message': 'hello'})
    LAST_WILL = json.dumps({"live": False, 'message': "last will"})
    END_OF_LIVE = json.dumps({"live": False, 'message': "goodbye"})

    def __init__(self, name: str):
        from board.mqtt_as import config as mqttconfig
        from configuration import Configuration
        (self.topic_live, _, _, _, self.topic_control) = Configuration.topics(name)
        # shared.EventConsumer.__init__(self, 'mqtt')
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
        self._messages_task = asyncio.create_task(self.messages())

    async def connect(self):
        try:
            await self.client.connect()
        except OSError as e:
            self.log.error(f"MQTT connecting FAILED")
            self.log.exception(e)

    async def messages(self):
        async for topic, msg, retained in self.client.queue:
            self.log.info(f"MQTT incoming - topic: '{topic.decode()}', message: '{msg.decode()}', retained: {retained}")


    async def on_up(self):
        while not self.exit:
            await self.client.up.wait()
            self.client.up.clear()
            self.log.info("MQTT connection established")
            await self.client.publish(self.topic_live, self.I_AM_ALIVE, True)
            await self.client.subscribe(self.topic_control)
            self.log.info(f"MQTT listen to topic: {self.topic_control}")
    #
    # async def consume(self, event: dict):
    #     self.log.info(f"MQTT event: {event}")
    #     topic = event.get('topic')
    #     data = event.get('data')
    #     if topic is None or data is None:
    #         await self.client.publish(self.topic_live, json.dumps({"live": True, "error": f"Cannot publish - topic or data is empty: {topic}, {data}"}))
    #     else:
    #         await self.client.publish(topic, json.dumps(data))

    def deinit(self):
        self.log.info("DEINIT")
        self.client.publish(self.topic_live, self.END_OF_LIVE, True)
        super().deinit()
        self._up_task.cancel()
        self._messages_task.cancel()
        self.client.disconnect()


class BoardApplication(shared.Named):

    def __init__(self, name: str):
        shared.Exit.init()
        if not hasattr(self, 'name'):
            shared.Named.__init__(self, name)
        self.start_time = time.ticks_ms()
        self.mqtt = None
        self.ws_server = BoardWebSocket({'self': self} | globals())

    def info(self):
        return json.dumps({
             'id': ubinascii.hexlify(machine.unique_id()).decode(),
            'uname': {key: eval('os.uname().' + key) for key in dir(os.uname()) if not key.startswith('__')},
            'frequency': machine.freq() / 1_000_000,
            'os_up_time': self.format_uptime(time.ticks_ms() // 1_000),
            'app_up_time': self.format_uptime((time.ticks_ms() - self.start_time) // 1_000),
            'mcu_temperature': esp32.mcu_temperature() if hasattr(esp32,'mcu_temperature') else None,
            'mem_alloc': gc.mem_alloc(),
            'mem_free': gc.mem_free(),
            'boot': Boot.get_instance().version,
            'ifconfig': Boot.get_instance().wifi.ifconfig(),
            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        })

    async def publish(self, topic, data, retain=False, qos=0, properties=None):
        await self.mqtt.client.publish(topic, json.dumps(data), retain, qos, properties)

    async def start(self):
        self.mqtt = MQTT(self.name)
        await self.mqtt.connect()

    async def _asyncio_entry(self):
        asyncio.create_task(self.start())
        asyncio.create_task(self.ws_server.start_server())
        while not shared.Exit.is_exit():
            await asyncio.sleep(1)
        self.ws_server.shutdown()

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
    def format_uptime(uptime):
        (minutes, seconds) = divmod(uptime, 60)
        (hours, minutes) = divmod(minutes, 60)
        (days, hours) = divmod(hours, 24)
        result = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        if days:
            result = "{:d} days ".format(days) + " " + result
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
