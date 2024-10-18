#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK

import argparse, argcomplete
import os
import sys

from common.common import Common
from  configuration import Configuration


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
    boards = list(Configuration.MAP["board"].keys())
    parser = argparse.ArgumentParser(
        prog='homectrl',
        description='DZEM HomeCtrl control command line tool',
        add_help=False)
    parser.add_argument("-h", "--help", action=_HelpAction)
    subparsers = parser.add_subparsers(help="Available commands", title="COMMANDS", required=True)

    connect = subparsers.add_parser("connect", help="Connect to specified command-line server")
    connect.add_argument("server_id", choices=boards, help="Available servers")
    # connect.add_argument("--direct", action="store_true", help="Direct connection to server (pass collector handling)")
    connect.set_defaults(command="connect")

    webrepl = subparsers.add_parser("webrepl", help="Connect to specified WEBREPL server")
    webrepl.add_argument("server_id", choices=boards, help="Available boards")
    webrepl.add_argument("--file", "-f",  help="Transfer file to the board")
    webrepl.set_defaults(command="webrepl")

    ping = subparsers.add_parser("ping", help="Ping to specified host")
    ping.add_argument("--count", "-c", type=int, help="Stop after sending count ECHO_REQUEST packets")
    ping.add_argument("server_id", choices=boards, help="Available hosts")

    ping.set_defaults(command="ping")

    collector = subparsers.add_parser("dev", help="DEV mode")
    collector.set_defaults(command="dev")

    db = subparsers.add_parser("db", help="Open database command-line tool")
    db.add_argument("db_action", choices=["cmd", "last"], default="cmd", nargs="?")
    db.add_argument("--sql", help="SQL query")
    db.set_defaults(command="db")

    mqtt = subparsers.add_parser("mqtt", help="Take an action on MQTT queue")
    mqtt.add_argument("mqtt_action", choices=["monitor", "delete", "publish"], default="monitor", nargs="?")
    mqtt_group = mqtt.add_mutually_exclusive_group()
    mqtt_group.add_argument("--topic", "-t", help="Topic name. Default: '{}/#'".format(Configuration.TOPIC_ROOT), nargs="+")
    mqtt_group.add_argument("--device", "-d", choices=boards, help="Available boards", nargs="+")
    mqtt.add_argument("--message", "-m", help="Message to publish", required="publish" in sys.argv)
    mqtt.add_argument("--retain", "-r", help="Retain the message", action="store_true")
    mqtt.set_defaults(command="mqtt")

    sms = subparsers.add_parser("sms", help="SMS tool")
    sms.add_argument("sms_action", choices=["balance", "parts"], default="balance", nargs="?")
    sms.add_argument("--message", "-m", help="Message to process", required='parts' in sys.argv)
    sms.set_defaults(command="sms")

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
        from backend import storage
        from backend.tools import json_serial

        for c in storage.entities():
            t = c.get_last()
            if t is not None:
                self.log("{} \t-> {}".format(type(t).__name__, json_serial(t.__dict__['__data__'])))

    def go(self, args):
        if args.command == "connect":
            from backend.tools import CommandLineClient
            self.log("Connecting to: {}".format(args.server_id))
            CommandLineClient(Configuration.get_communication(args.server_id), args.server_id).start()

        elif args.command == "ping":
            ping_args = ""
            if args.count:
                ping_args = " -c {}".format(args.count)
            os.system("ping {} {}".format(ping_args, Configuration.get_config(args.server_id)["host"]))

        elif args.command == "webrepl":
            host = Configuration.get_config(args.server_id)["host"]
            password = Configuration.get_config(args.server_id)["webrepl_password"]
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
                db = Configuration.get_database_config()
                cmd = "PGPASSWORD={} psql -U {} {}".format(db["password"], db["username"], db["db"])
                if args.sql:
                    os.system("echo \"{}\" | {}".format(args.sql, cmd))
                else:
                    os.system(cmd)
            elif args.db_action == "last":
                self.list_db()

        elif args.command == "mqtt":
            from backend.tools import MQTTMonitor, MQTTClient

            if args.mqtt_action == "monitor":
                if args.device:
                    topic = (
                        list(map(lambda device: f"{Configuration.TOPIC_ROOT}/device/{device}/#", args.device))
                        + list(map(lambda device: f"{Configuration.TOPIC_ROOT}/onair/+/{device}", args.device)))
                elif args.topic:
                    topic = args.topic
                else:
                    topic = "{}/#".format(Configuration.TOPIC_ROOT)
                MQTTMonitor(topic).start()

            elif args.mqtt_action == "delete":
                if args.topic:
                    client = MQTTClient()
                    for t in args.topic:
                        client.publish(t, "", retain=True)
                else:
                    raise ValueError("Specify the topic to delete")

            elif args.mqtt_action == "publish":
                if args.topic:
                    client = MQTTClient()
                    for t in args.topic:
                        client.publish(t, args.message, retain=args.retain)
                else:
                    raise ValueError("Specify the message topic to publish")

        elif args.command == "sms":
            from backend.sms import SMS
            if args.sms_action == "balance":
                print(SMS().balance())
            elif args.sms_action == "parts":
                message = args.message
                print("Checking number of parts for message: {}".format(message))
                result = SMS().parts_count(message)
                print("RESULT: {}".format(result))


if __name__ == "__main__":
    args = parse_args()
    # print("=============")
    # print(vars(args))
    HomeCtrl().go(args)
