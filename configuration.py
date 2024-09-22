import os
import datetime
import decimal
import json

from common.communication import SocketCommunication


class Configuration:
    PATH = os.path.dirname(os.path.realpath(__file__))
    MAP = json.loads(open(os.path.join(PATH,"homectrl-map.json")).read())
    DATABASE = os.path.join(PATH, "homectrl.db")
    COLLECTOR = "collector"

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


class HomeCtrlJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def json_serial(obj):
    return json.dumps(obj, cls=HomeCtrlJsonEncoder)


def json_deserial(json_str):
    return json.loads(json_str, parse_float=lambda x: round(decimal.Decimal(x), 10))


