import json

# from umqtt.robust import MQTTClient
from board.robust2 import MQTTClient

from common.common import Common, time_ms


class MQTTPublisher(Common):

    KEEPALIVE_SEC = 60
    PING_EVERY_MS = 35 * 1_000
    I_AM_ALIVE = json.dumps({"live": True})

    def __init__(self, name, topic_root="homectrl"):
        super().__init__(name)
        self.topic = topic_root + "/{}".format(name)
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

    def publish(self, msg, topic=None, retain=True):
        if not self.connected:
            self.connect()
        try:
            if not topic:
                topic = self.topic

            if isinstance(msg, dict):
                msg = json.dumps(msg)
            if not isinstance(msg, str):
                raise ValueError(f"Unsupported message type: {type(msg)}")

            self.mqtt.publish(topic, msg, retain)
            self.last_message_time = time_ms()
        except OSError as e:
            self.connected = False
            self.log("Error while publishing topic {}: {}".format(topic, e))

    def publish_error(self, msg: str):
        self.publish({
            "live": False,
            "error": msg
        }, self.live_topic)

    def ping(self):
        if self.last_message_time is None or time_ms() - self.last_message_time > self.PING_EVERY_MS:
            self.publish(self.I_AM_ALIVE, self.live_topic, False)

    def close(self):
        self.mqtt.publish(self.live_topic, json.dumps({"live": False, "error": "goodbye"}), True)
        self.mqtt.disconnect()
        self.connected = False

