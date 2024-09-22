#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse, argcomplete
import os
import storage
from client import CommandLineClient
from common.common import Common
from configuration import Configuration, json_serial
from monitor import Monitor


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
    ping.add_argument("--count", "-c", type=int, help="Stop after sending count ECHO_REQUEST packets")
    ping.add_argument("server_id", choices=to_connect, help="Available hosts")

    ping.set_defaults(command="ping")

    collector = subparsers.add_parser("dev", help="DEV mode")
    collector.set_defaults(command="dev")

    db = subparsers.add_parser("db", help="Open database command-line tool")
    db.add_argument("db_action", choices=["cmd", "last"], default="cmd", nargs="?")
    db.add_argument("--sql", help="SQL query")
    db.set_defaults(command="db")

    mqtt = subparsers.add_parser("mqtt", help="Monitor Mosquitto queue")
    mqtt.add_argument("mqtt_action", choices=["monitor"], default="monitor", nargs="?")
    mqtt.add_argument("--topic", "-t", help="Topic name. Default: '/homectrl/#")
    mqtt.set_defaults(command="mqtt")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # print("DEBUG: {}".format(vars(args)))
    # print("DEBUG: {}".format(args._get_args()))
    # print("DEBUG: {}".format(dir(args)))
    return args


class HomeCtrl(Common):
    def __init__(self):
        super().__init__("HOMECTRL")

    def list_db(self):
        for c in storage.entities():
            t = c.get_last()
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
            ping_args = ""
            if args.count:
                ping_args = " -c {}".format(args.count)
            os.system("ping {} {}".format(ping_args, Configuration.get_config(args.server_id)["host"]))

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
                cmd = "PGPASSWORD=homectrl_dba psql -U homectrl homectrl"
                if args.sql:
                    os.system("echo \"{}\" | {}".format(args.sql, cmd))
                else:
                    os.system(cmd)
            elif args.db_action == "last":
                self.list_db()

        elif args.command == "mqtt":
            if args.mqtt_action == "monitor":
                topic = args.topic if args.topic else "homectrl/#"
                Monitor(topic).start()


if __name__ == "__main__":
    args = parse_args()
    # print("=============")
    # print(vars(args))
    HomeCtrl().go(args)
