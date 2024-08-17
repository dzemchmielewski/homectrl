import json
import os

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
