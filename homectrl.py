#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse, argcomplete
import os
import sys

from backend.tools import WebREPLClient
from common.common import Common
from  configuration import Configuration, Topic

import logging
logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(name)s] %(message)s"))
logger = logging.getLogger("HOMECTRL")

# class _HelpAction(argparse._HelpAction):
#
#     def __call__(self, parser, namespace, values, option_string=None):
#         parser.print_help()
#         print("\n")
#
#         # retrieve subparsers from parser
#         subparsers_actions = [
#             action for action in parser._actions
#             if isinstance(action, argparse._SubParsersAction)]
#         # there will probably only be one subparser_action,
#         # but better save than sorry
#         for subparsers_action in subparsers_actions:
#             # get all subparsers and print help
#             for choice, subparser in subparsers_action.choices.items():
#                 print("COMMAND '{}'".format(choice))
#                 print(subparser.format_help())
#
#         parser.exit()


class HomeCtrl(Common):

    class Formatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter):
        pass

    class TopicCompleter(argcomplete.completers.BaseCompleter):
        TOPICS = {
            "homectrl/" : {
                "homectrl/#" : None,
                "homectrl/device/": {
                    "homectrl/device/#": None
                },
                "homectrl/onair/": {
                    "homectrl/onair/#": None,
                    "homectrl/onair/activity/": {
                        "homectrl/onair/activity/#": None,
                        "homectrl/onair/activity/laundry": None,
                        "homectrl/onair/activity/astro": None,
                        "homectrl/onair/activity/meteo": {
                            "homectrl/onair/activity/meteo": None,
                            "homectrl/onair/activity/meteo/#": None,
                            "homectrl/onair/activity/meteo/temperature": None,
                            "homectrl/onair/activity/meteo/precipitation": None,
                            "homectrl/onair/activity/meteo/pressure": None,
                        }
                    }
                }
            }
        }

        def __init__(self, boards: [str]):
            super().__init__()
            # Dynamically add boards to topics
            device_topics = self.TOPICS["homectrl/"]["homectrl/device/"]
            for board in boards:
                device_topics[f"homectrl/device/{board}/#"] = None

        def getlist(self, input, topics: dict) -> [str]:
            results = []
            for key, value in topics.items():
                if key.startswith(input):
                    # If input matches the key, and value is a dict, return its keys
                    if isinstance(value, dict):
                        results.extend(value.keys())
                    else:
                        results.append(key)
                elif input.startswith(key):
                    # If input is longer, go deeper
                    if isinstance(value, dict):
                        results.extend(self.getlist(input, value))
            return results

        def __call__(self, prefix, parsed_args, **kwargs):
            return self.getlist(prefix, self.TOPICS)


    def __init__(self):
        super().__init__("HOMECTRL")
        from devel.esp32_setup import Esp32Setup
        from devel.firmware import Firmware
        from devel.fontconv import FontConverter
        self.devel = [Esp32Setup, Firmware, FontConverter]

    def parse_args(self):
        boards = list(Configuration.MAP["board"].keys())
        parser = argparse.ArgumentParser(
            prog='homectrl',
            description='DZEM HomeCtrl control command line tool',
            add_help=True, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        # parser.add_argument("-h", "--help", action=_HelpAction)
        subparsers = parser.add_subparsers(help="Available commands", title="COMMANDS", required=True)

        connect = subparsers.add_parser("connect", help="Connect to specified HOMECtrl command-line server", formatter_class=self.Formatter)
        connect.add_argument("server_id", choices=boards, help="Available HOMECtrl boards")
        connect.add_argument("-nf", "--no-format", help="Do not format json response", default=False, action="store_true")
        connect.add_argument("--exit", "-e", help="Send a HOMECtrl board the server_exit call", default=False, action="store_true")
        connect.add_argument("-v1", help="Legacy call to server V=1", default=False, action="store_true")
        connect.set_defaults(command="connect")

        webrepl = subparsers.add_parser("webrepl", help="Connect to specified WEBREPL server", formatter_class=self.Formatter)
        webrepl.add_argument("server_id", choices=boards, help="Available boards")
        webrepl_file_group = webrepl.add_mutually_exclusive_group()
        webrepl_file_group.add_argument("--file", "-f",  help="Transfer file(s) TO the board", nargs="+")
        webrepl_file_group.add_argument("--get", "-g",  help="Transfer file FROM the board")
        webrepl_file_group.add_argument("--exit", "--reset", "-e", default=False, action="store_true",
                                        help="Send sys.exit() command, aka soft reset")
        webrepl_file_group.add_argument("--reboot", "-r", default=False, action="store_true",
                                        help="Send machine.reset() command aka hard reset/reboot")
        webrepl_file_group.add_argument("--statement", "-s",  help="Execute a single statement and exit")
        webrepl.set_defaults(command="webrepl")

        ping = subparsers.add_parser("ping", help="Ping to specified host", formatter_class=self.Formatter)
        ping.add_argument("--count", "-c", type=int, help="Stop after sending count ECHO_REQUEST packets")
        ping.add_argument("server_id", choices=boards, help="Available hosts")

        ping.set_defaults(command="ping")

        db = subparsers.add_parser("db", help="Open database command-line tool", formatter_class=self.Formatter)
        db.add_argument("db_action", choices=["cmd", "last"], default="cmd", nargs="?")
        db.add_argument("--sql", help="SQL query")
        db.set_defaults(command="db")

        mqtt = subparsers.add_parser("mqtt", help="Take an action on MQTT queue", formatter_class=self.Formatter)
        mqtt.add_argument("mqtt_action", choices=["monitor", "delete", "publish"], default="monitor", nargs="?")
        mqtt_group = mqtt.add_mutually_exclusive_group()
        mqtt_group.add_argument("--topic", "-t", help="Topic name. Default: '{}/#'".format(Topic.Root), nargs="+")\
            .completer=self.TopicCompleter(boards)
        # mqtt_group.add_argument("--topic-prefix", help="Default prefix of the topic that is added to each topic specified by  '-t' option.", default="{}/".format(Topic.Root))
        mqtt_group.add_argument("--device", "-d", choices=boards, help="Available boards", nargs="+")

        mqtt.add_argument("--message", "-m", help="Message to publish", required="publish" in sys.argv)
        mqtt.add_argument("--retain", "-r", help="Retain the message", action="store_true")
        mqtt.set_defaults(command="mqtt")

        sms = subparsers.add_parser("sms", help="SMS tool", formatter_class=self.Formatter)
        sms.add_argument("sms_action", choices=["balance", "parts"], default="balance", nargs="?")
        sms.add_argument("--message", "-m", help="Message to process", required='parts' in sys.argv)
        sms.set_defaults(command="sms")

        devel = subparsers.add_parser("devel", help="Less trivial development tools", formatter_class=self.Formatter)
        devel_subparsers = devel.add_subparsers(title="Devel tools", required=True)
        for dev in self.devel:
            (devel_subparsers
             .add_parser(dev.argparser.prog, parents=[dev.argparser], conflict_handler="resolve", formatter_class=dev.argparser.formatter_class)
             .set_defaults(devel_command=dev.argparser.prog))
        devel.set_defaults(command="devel")

        argcomplete.autocomplete(parser)
        args = parser.parse_args()

        # logger.debug("DEBUG ARGS: {}".format(vars(args)))
        return args

    def list_db(self):
        from backend import storage
        from backend.tools import json_serial

        for c in storage.entities():
            t = c.get_last()
            if t is not None:
                logger.info("{} \t-> {}".format(type(t).__name__, json_serial(t.__dict__['__data__'])))

    def run(self):
        args = self.parse_args()

        if args.command == "connect":
            if args.v1:
                if args.exit:
                    from backend.tools import Client
                    logger.info("Connecting to: {}".format(args.server_id))
                    client = Client(Configuration.get_communication(args.server_id), args.server_id)
                    logger.info(" >>  server_exit")
                    logger.info(f" <<  {client.interact('server_exit')}")
                else:
                    from backend.tools import CommandLineClient
                    logger.info("Connecting to: {}".format(args.server_id))
                    CommandLineClient(Configuration.get_communication(args.server_id), args.server_id, not args.no_format).start()
            else:
                from backend.tools import WSCommandLineClient
                logger.info("Connecting to: {}".format(args.server_id))
                if args.exit:
                    client = WSCommandLineClient(args.server_id, not args.no_format)
                    client.ws.send("shared.Exit.go()")
                    client.ws.close()
                else:
                    WSCommandLineClient(args.server_id, not args.no_format).start()

        elif args.command == "ping":
            ping_args = ""
            if args.count:
                ping_args = " -c {}".format(args.count)
            os.system("ping {} {}".format(ping_args, Configuration.get_config(args.server_id)["host"]))

        elif args.command == "webrepl":
            with WebREPLClient(args.server_id) as repl:
                if args.exit:
                    repl.ws.writetext("import sys; sys.exit()".encode("utf-8") + b"\r\n")
                elif args.reboot:
                    repl.ws.writetext("import machine; machine.reset()".encode("utf-8") + b"\r\n")
                elif args.file:
                    for file in args.file:
                        repl.put_file(file, file)
                elif args.get:
                    repl.get_file(args.get, args.get)
                elif args.statement:
                    repl.repl([args.statement])
                else:
                    repl.do_repl()

        elif args.command == "db":
            if args.db_action == "cmd":
                db = Configuration.get_database_config()
                cmd = "PGPASSWORD={} psql -h {} -p {} -U {} {}".format(db["password"], db["host"], db["port"], db["username"], db["db"])
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
                        list(map(lambda device: Topic.Device.format(device, "#"), args.device))
                        + list(map(lambda device: Topic.OnAir.format("+", device), args.device)))
                elif args.topic:
                    topic = args.topic
                else:
                    topic = "{}/#".format(Topic.Root)
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
                logger.info(SMS().balance())
            elif args.sms_action == "parts":
                message = args.message
                logger.info("Checking number of parts for message: {}".format(message))
                result = SMS().parts_count(message)
                logger.info("RESULT: {}".format(result))

        elif args.command == "devel":
            dev_cls = next((cls for cls in self.devel if cls.argparser.prog == args.devel_command), None)
            dev_cls(args).run()


if __name__ == "__main__":
    HomeCtrl().run()
