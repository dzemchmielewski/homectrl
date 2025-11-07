import os
import json
import re
from enum import Enum

from common.communication import SocketCommunication


secret_key_regexp = re.compile(r"\$\{(.+)\}")


def apply_secrets(input, secrets):
    if isinstance(input, dict):
        result = {}
        for k, v in input.items():
            result[k] = apply_secrets(v, secrets)
        return result
    elif hasattr(input, '__iter__') and not isinstance(input, str):
        result = []
        for item in input:
            result.append(apply_secrets(item, secrets))
        return result
    elif isinstance(input, str) and (m := secret_key_regexp.match(input)):
        secret_key = m.group(1)
        return secrets.get(secret_key) if secrets.get(secret_key) else input
    else:
        return input


class _Topic:
    def __init__(self, topic: str, parts: int):
        self.topic = topic + "/" + "/".join(["{}"] * parts)
        self.topic_re = re.compile(topic + "/" + "/".join(["(.+)"] * parts))

    def format(self, *parts) -> str:
        return self.topic.format(*parts)

    def parse(self, topic: str) -> tuple:
        if m := self.topic_re.match(topic):
            return m.groups()
        return None

    def is_topic(self, topic: str) -> bool:
        return self.topic_re.match(topic) is not None


class Topic:

    Root = "homectrl"

    class Device:
        # homectrl/device/<name>/<facility>
        _topic = _Topic("homectrl/device", 2)
        parse = _topic.parse
        format = _topic.format
        is_topic = _topic.is_topic

        class Facility(Enum):
            live = "live"
            data = "data"
            capabilities = "capabilities"
            state = "state"
            control = "control"

            def __str__(self):
                return self.name

    class OnAir:
        # homectrl/onair/<facet>/<name>
        _topic = _Topic("homectrl/onair", 2)
        format = _topic.format
        parse = _topic.parse
        is_topic = _topic.is_topic

        class Facet(Enum):
            # There are some more dynamic facets here, like light, presence, live, etc...
            activity = "activity"

            def __str__(self):
                return self.name


class Configuration:
    PATH = os.path.dirname(os.path.realpath(__file__))
    MAP = json.loads(open(os.path.join(PATH, "homectrl-map.json")).read())

    ONAIR_TOPIC_SUBSCRIPTIONS = ["homectrl/device/+", "homectrl/device/+/live"]

    if os.path.exists(os.path.join(PATH, "secrets.json")):
        secrets = json.loads(open(os.path.join(PATH, "secrets.json")).read())
        MAP = apply_secrets(MAP, secrets)
    else:
        raise BaseException("secrets.json file not found!")

    @staticmethod
    def get_config(server_id):
        if server_id in Configuration.MAP["board"].keys():
            return Configuration.MAP["board"][server_id]
        elif server_id == Configuration.COLLECTOR:
            return Configuration.MAP[Configuration.COLLECTOR]
        raise NameError("No server with id {} found".format(server_id))

    @staticmethod
    def get_communication(server_id, name="socket"):
        config = Configuration.get_config(server_id)
        return SocketCommunication(name, config["host"], config["port"], is_server=False, read_timeout=30, debug=config["debug"])

    @staticmethod
    def get_database_config():
        return Configuration.MAP["database"]

    @staticmethod
    def get_mqtt_config():
        return Configuration.MAP["mqtt"]

    @staticmethod
    def get_charts_config():
        return Configuration.MAP["charts"]

    @staticmethod
    def get_sms_config():
        return Configuration.MAP["sms"]

    @staticmethod
    def get(name: str):
        return Configuration.MAP.get(name, None)
