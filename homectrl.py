import argparse
import datetime
import decimal
import json
import os
from time import sleep

from client import CommandLineClient, Client
from common.common import Common
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


import storage


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


class _HelpAction(argparse._HelpAction):

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        print("\n")

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]
        # there will probably only be one subparser_action,
        # but better save than sorry
        for subparsers_action in subparsers_actions:
            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                print("COMMAND '{}'".format(choice))
                print(subparser.format_help())

        parser.exit()


def parse_args():
    parser = argparse.ArgumentParser(
        prog='homectrl',
        description='DZEM HomeCtrl control command line tool',
        add_help=False)
    parser.add_argument("-h", "--help", action=_HelpAction)
    subparsers = parser.add_subparsers(help="Available commands", title="COMMANDS", required=True)

    connect = subparsers.add_parser("connect", help="Connect to specified command-line server")
    to_connect = list(Configuration.MAP["board"].keys())
    to_connect.append(Configuration.COLLECTOR)
    connect.add_argument("server_id", choices=to_connect, help="Available servers")
    # connect.add_argument("--direct", action="store_true", help="Direct connection to server (pass collector handling)")
    connect.set_defaults(command="connect")

    webrepl = subparsers.add_parser("webrepl", help="Connect to specified WEBREPL server")
    to_connect = list(Configuration.MAP["board"].keys())
    webrepl.add_argument("server_id", choices=to_connect, help="Available boards")
    webrepl.add_argument("--file", "-f",  help="Transfer file to the board")
    webrepl.set_defaults(command="webrepl")

    ping = subparsers.add_parser("ping", help="Ping to specified host")
    ping.add_argument("server_id", choices=to_connect, help="Available hosts")
    ping.set_defaults(command="ping")

    collector = subparsers.add_parser("dev", help="DEV mode")
    collector.set_defaults(command="dev")

    db = subparsers.add_parser("db", help="Open database command-line tool")
    db.add_argument("db_action", choices=["cmd", "last"], default="cmd", nargs="?")
    db.add_argument("--sql", help="SQL query")
    db.set_defaults(command="db")

    args = parser.parse_args()

    # print("DEBUG: {}".format(vars(args)))
    # print("DEBUG: {}".format(args._get_args()))
    # print("DEBUG: {}".format(dir(args)))
    return args


class HomeCtrl(Common):
    def __init__(self):
        super().__init__("HOMECTRL")

    def list_db(self):
        for c in storage.COLLECTIONS:
            for key, value in Configuration.MAP["board"].items():
                if value["collect"]:
                    t = c.get_last(key)
                    if t is not None:
                        self.log("{} \t-> {}".format(type(t).__name__, json_serial(t.__dict__['__data__'])))

    def go(self, args):
        if args.command == "connect":
            if args.server_id != Configuration.COLLECTOR:
                self.log("Connecting to: {}".format(args.server_id))
                CommandLineClient(Configuration.get_communication(args.server_id), args.server_id).start()
            else:
                CommandLineClient(Configuration.get_communication(Configuration.COLLECTOR), "COLLECTOR").start()

        elif args.command == "ping":
            os.system("ping {}".format(Configuration.get_config(args.server_id)["host"]))

        elif args.command == "webrepl":
            password = "dzemHrome"
            host = Configuration.get_config(args.server_id)["host"]
            if args.file:
                cmd = "webrepl -p {password} {file} {host}:/{file}".format(host=host, password=password, file=args.file)
            else:
                cmd = "webrepl -p {password} {host}".format(host=host, password=password)
            self.log(cmd)
            os.system(cmd)

        elif args.command == "dev":
            pass

        elif args.command == "db":
            if args.db_action == "cmd":
                if args.sql:
                    os.system("echo \"{}\" | /usr/bin/sqlite3 {}".format(args.sql, Configuration.DATABASE))
                else:
                    os.system("/usr/bin/sqlite3 {}".format(Configuration.DATABASE))
            elif args.db_action == "last":
                self.list_db()


if __name__ == "__main__":
    args = parse_args()
    # print("=============")
    # print(vars(args))
    HomeCtrl().go(args)
