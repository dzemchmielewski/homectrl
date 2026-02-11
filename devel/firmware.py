#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete
import datetime
import fileinput
import glob
import os
import re
from pathlib import Path

import argcomplete
import argparse
import shutil

from backend.tools import WebREPLClient
from configuration import Configuration
from devel.development import RawTextArgumentDefaultsHelpFormatter, str2bool


class Firmware:

    INC_st7789 = "st7789"
    INC_desk = "desk"
    include_choices = [INC_st7789, INC_desk]

    include_help = f"""
    {INC_st7789} - driver for TFT-LCD display
    {INC_desk} - custom python modules for for specific "desk" project
    """

    boards = list(Configuration.MAP["board"].keys())
    argparser = argparse.ArgumentParser(
        prog='fw',
        description='DZEM HomeCtrl Devel - Firmware tools',
        add_help=True, formatter_class=RawTextArgumentDefaultsHelpFormatter)

    subparsers = argparser.add_subparsers(help="Available commands", title="COMMANDS", required=True)

    status = subparsers.add_parser("status", help="OTA status", formatter_class=RawTextArgumentDefaultsHelpFormatter)
    status.add_argument("server_id", choices=boards, help="Available boards")
    status.add_argument("--homectrl-exit", "-he", type=str2bool, help="Try to exit HomeCtrl server on the board", default=True)
    status.set_defaults(ota_command="status")

    update = subparsers.add_parser("update", help="OTA update", formatter_class=RawTextArgumentDefaultsHelpFormatter)
    update.add_argument("server_id", choices=boards, help="Available boards")
    update.add_argument("--url", "-u", type=str, help="Firmware file URL", required=True)
    update.add_argument("--homectrl-exit", "-he", type=str2bool, help="Try to exit HomeCtrl server on the board", default=True)
    update.set_defaults(ota_command="update")

    commit = subparsers.add_parser("commit", help="OTA update commit", formatter_class=RawTextArgumentDefaultsHelpFormatter)
    commit.add_argument("server_id", choices=boards, help="Available boards")
    commit.add_argument("--homectrl-exit", "-he", type=str2bool, help="Try to exit HomeCtrl server on the board", default=True)
    commit.set_defaults(ota_command="commit")

    build = subparsers.add_parser("build", help="Build micropython firmware", formatter_class=RawTextArgumentDefaultsHelpFormatter)
    build.add_argument("--port", "-p", choices=["C3", "S3", "GENERIC", "C6"], help="Available ports", required=True)
    build.add_argument("--version", "-v", help="Version number to put into the firmware",
                       default=datetime.datetime.now().strftime("%Y%m%d_%H_%M"))
    build.add_argument("--src-micropython", help="Micropython ESP32 source directory",
                       default="/home/dzem/MP_BUILD/micropython/ports/esp32/")
    build.add_argument("--src-esp-idf", help="ESP-IDF source directory",
                       default="/home/dzem/MP_BUILD/esp-idf/")
    build.add_argument("--src-homectrl", help="HOMECtrl source directory",
                       default=os.path.dirname(os.path.dirname(os.path.normpath(__file__))))
    build.add_argument("--include", "-i", nargs='+', required=False, choices=include_choices, help=include_help, default=[])
    build.set_defaults(ota_command="build")

    @classmethod
    def parse_args(cls, args=None):
        argcomplete.autocomplete(cls.argparser)
        return cls.argparser.parse_args(args)

    def __init__(self, parsed_args):
        self.args = parsed_args
        print(parsed_args)

    @staticmethod
    def copy(src, dest):
        if not os.path.exists(src):
            raise ValueError(f"Directory {src} not found!")

        if os.path.isdir(src):
            Path(dest).mkdir(parents=True, exist_ok=True)
            for filename in os.listdir(src):
                if filename.endswith('.py'):
                    print(f"{src}/{filename} -> {dest}")
                    shutil.copy(f"{src}/{filename}", dest)
        else:
            Path(os.path.dirname(dest)).mkdir(parents=True, exist_ok=True)
            print(f"{src} -> {dest}")
            shutil.copyfile(src, dest)

    def sync_frozen_py(self):
        for sub in ["board", "toolbox"]:
            print(f"{self.args.src_homectrl}/micropython/{sub} -> {self.args.src_micropython}/modules/{sub}")
            try:
                shutil.rmtree(f"{self.args.src_micropython}/modules/{sub}")
            except FileNotFoundError:
                pass
            shutil.copytree(f"{self.args.src_homectrl}/micropython/{sub}", f"{self.args.src_micropython}/modules/{sub}")

        for file in glob.glob(rf"{self.args.src_homectrl}/micropython/*.py"):
            print(f"{file} -> {self.args.src_micropython}/modules/")
            shutil.copy(file, f"{self.args.src_micropython}/modules/")

    def apply_boot_version(self):
        boot_version_pattern = re.compile("version = (.+)")
        with fileinput.FileInput(f"{self.args.src_micropython}/modules/board/boot.py", inplace=True) as file:
            for line in file:
                print(re.sub(boot_version_pattern, f"version = '{self.args.version}'", line), end='')

    def apply_port_name(self):
        boot_version_pattern = re.compile("port = (.+)")
        with fileinput.FileInput(f"{self.args.src_micropython}/modules/board/boot.py", inplace=True) as file:
            for line in file:
                print(re.sub(boot_version_pattern, f"port = '{self.args.port}'", line), end='')

    def run(self):
        if self.args.ota_command == "build":
            print(f"Building version: {self.args.version} for ESP32-{self.args.port}")

            # for sub in ["board", "modules", "common",
            #             "common/platform/__init__.py", "common/platform/rp2pico.py"]:
            #     self.copy(f"{self.args.src_homectrl}/{sub}", f"{self.args.src_micropython}/modules/{sub}")
            #
            # self.copy(f"{self.args.src_homectrl}/micropython-stdlib", f"{self.args.src_micropython}/modules/")

            try:
                shutil.rmtree(f"{self.args.src_micropython}/modules/desk_fw")
            except FileNotFoundError:
                pass

            self.sync_frozen_py()
            self.apply_boot_version()
            self.apply_port_name()

            if Firmware.INC_desk in  self.args.include:
                shutil.copytree(f"{self.args.src_homectrl}/devices/desk/desk_fw", f"{self.args.src_micropython}/modules/desk_fw/")

            make_opt = ""
            if Firmware.INC_st7789 in self.args.include:
                make_opt += " USER_C_MODULES=/home/dzem/MP_BUILD/st7789_mpy/st7789/ "

            board_name = f"ESP32_GENERIC_{self.args.port}" if self.args.port != "GENERIC" else "ESP32_GENERIC"

            build_cmd = (f"/bin/bash -c "
                "'"
                f" cd {self.args.src_micropython}"
                f" && source {self.args.src_esp_idf}/export.sh "
                f" && make BOARD={board_name} BOARD_VARIANT=OTA {make_opt} all"
                "'")
            print(f"Build command: {build_cmd}")

            ret_code = os.system(build_cmd)

            if ret_code == 0:
                shutil.copyfile(f"{self.args.src_micropython}/build-{board_name}-OTA/micropython.bin",
                                f"/www/micropython-esp32-{self.args.port.lower()}-{self.args.version}.bin")
                print("BUILD DONE")
                print(f"http://pi5.home/micropython-esp32-{self.args.port.lower()}-{self.args.version}.bin")

        else:
            with WebREPLClient(self.args.server_id) as repl:
                if self.args.ota_command == "status":
                    print("")
                    print(f"<< {repl.sendcmd('import ota.status; ota.status.status()').decode()}")
                    print(f"<< {repl.sendcmd('boot.version').decode()}")
                elif self.args.ota_command == "update":
                    commands = [
                        "import ota.update",
                        f"ota.update.from_file('{self.args.url}', reboot=False)"]
                    repl.repl(commands)
                    repl.ws.writetext("import machine; machine.reset()".encode("utf-8") + b"\r\n")
                elif self.args.ota_command == "commit":
                    print(f"<< {repl.sendcmd('import ota.rollback; ota.rollback.cancel()').decode()}")


if __name__ == "__main__":
    Firmware(Firmware.parse_args()).run()

    # c = [
    #     "import time",
    #     "for i in range(3, 0,  -1):\r\nprint(f\'Hard reset in {i} seconds...\\r', end=('\\r\\n' if i == 1 else ''))\r\ntime.sleep(1)\r\n\r\n\r\n",
    #     "print('')"]
    # repl.repl(c)
