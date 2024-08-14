import json

import time
from umqtt.robust import MQTTClient

from common.common import Common, time_ms


class MQTTPublisher(Common):

    KEEPALIVE_SEC = 60
    PING_EVERY_MS = 35 * 1_000
    I_AM_ALIVE = json.dumps({"live": True})

    def __init__(self, name):
        super().__init__(name)
        self.topic = "homectrl/{}".format(name)
        self.live_topic = self.topic + "/live"
        self.mqtt = MQTTClient(self.topic, "192.168.0.20", user="mqtt", password="emkutete", keepalive=self.KEEPALIVE_SEC)
        self.mqtt.set_last_will(self.live_topic, json.dumps({"live": False, "error": "last will"}))
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
            if self.last_message_time and time_ms() - self.last_message_time > self.PING_EVERY_MS:
                self.mqtt.publish(self.live_topic, self.I_AM_ALIVE)
                self.last_message_time = time_ms()
        except OSError as e:
            self.connected = False
            self.log("Error while pinging: {}".format(e))

    def close(self):
        self.mqtt.publish(self.live_topic, json.dumps({"live": False, "error": "goodbye"}))
        self.mqtt.disconnect()
        self.connected = False

