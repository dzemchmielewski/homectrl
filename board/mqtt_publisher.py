import json
from umqtt.robust import MQTTClient

from common.common import Common, time_ms


class MQTTPublisher(Common):

    KEEPALIVE_SEC = 30
    PING_EVERY_MS = 25 * 1_000

    def __init__(self, name):
        super().__init__(name)
        self.topic = "homectrl/{}".format(name)
        self.mqtt = MQTTClient(self.topic, "192.168.0.20", user="mqtt", password="emkutete", keepalive=self.KEEPALIVE_SEC)
        self.mqtt.set_last_will(self.topic, json.dumps({"live": False}))
        self.connected = False
        self.last_message_time = None

    def connect(self):
        try:
            self.log("MQTT connecting...")
            self.mqtt.connect()
            self.connected = True
            self.log("MQTT connected")
        except OSError as e:
            self.connected = False
            self.log("Error while connecting: {}".format(e))

    def publish(self, msg: dict):
        if not self.connected:
            self.connect()
        try:
            self.mqtt.publish(self.topic, json.dumps(msg))
            self.last_message_time = time_ms()
        except OSError as e:
            self.connected = False
            self.log("Error while publishing: {}".format(e))

    def publish_error(self, msg: str):
        self.publish({
            "live": False,
            "error": msg
        })
        self.last_message_time = time_ms()

    def ping(self):
        try:
            if time_ms() - self.last_message_time > self.PING_EVERY_MS:
                self.mqtt.ping()
                self.last_message_time = time_ms()
        except OSError as e:
            self.connected = False
            self.log("Error while pinging: {}".format(e))

    def close(self):
        self.mqtt.disconnect()
        self.connected = False

