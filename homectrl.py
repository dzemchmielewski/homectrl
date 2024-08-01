import argparse
import json
import os

from client import CommandLineClient, Client
from common.communication import SocketCommunication

PATH = os.path.dirname(os.path.realpath(__file__))
MAP = json.loads(open(os.path.join(PATH,"homectrl-map.json")).read())


class Configuration:
    MAP = json.loads(open(os.path.join(PATH,"homectrl-map.json")).read())


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
    to_connect = list(MAP["board"].keys())
    to_connect.append("collector")
    connect.add_argument("server_id", choices=to_connect, help="Available servers")
    connect.set_defaults(command="connect")

    collector = subparsers.add_parser("dev", help="DEV mode")
    collector.set_defaults(command="dev")

    db = subparsers.add_parser("db", help="Open database command-line tool")
    db.set_defaults(command="db")

    args = parser.parse_args()

    # print("DEBUG: {}".format(vars(args)))
    # print("DEBUG: {}".format(args._get_args()))
    # print("DEBUG: {}".format(dir(args)))
    return args


if __name__ == "__main__":
    args = parse_args()
    # print("=============")
    # print(vars(args))

    if args.command == "connect":
        if args.server_id in MAP["board"].keys():
            conf = Configuration.MAP["board"][args.server_id]
            CommandLineClient(SocketCommunication("SOCKET", conf["host"], conf["port"], is_server=False, read_timeout=30, debug=conf["debug"])).start()
        elif args.server_id == "collector":
            conf = Configuration.MAP["collector"]
            CommandLineClient(SocketCommunication("SOCKET", conf["host"], conf["port"], is_server=False, read_timeout=30, debug=conf["debug"])).start()

    elif args.command == "dev":
        conf = Configuration.MAP["collector"]
        client = Client(SocketCommunication("SOCKET", conf["host"], conf["port"], is_server=False, read_timeout=30, debug=conf["debug"]))
        list = client.interact("list")
        print("LIST: {}".format(list))
        client.close()

    elif args.command == "db":
        os.system("/usr/bin/sqlite3 {}".format(os.path.join(PATH, "homectrl.db")))
