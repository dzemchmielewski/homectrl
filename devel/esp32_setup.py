#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import os
import tempfile
import uuid
import argparse, argcomplete

from devel.development import RawTextArgumentDefaultsHelpFormatter, str2bool


class Esp32Setup:
    argparser = argparse.ArgumentParser(
        prog='esp32setup',
        description='DZEM HomeCtrl Devel - ESP32 board setup',
        add_help=True, formatter_class=RawTextArgumentDefaultsHelpFormatter)

    argparser.add_argument('--dest-board', type=str, required=False, dest="dest_board", default="/pyboard/",
                           help="Destination board name")
    argparser.add_argument('--dest-boot', type=str, required=False, dest="dest_boot", default="boot.py",
                           help="Destination boot file name")
    argparser.add_argument('--dest-main', type=str, required=False, dest="dest_main", default="main.py",
                           help="Destination main file name")

    argparser.add_argument('--boot-pin', '-bp', type=int, required=False, dest="pin",
                           help="Pin number to use for boot notification.\nESP32-C3 super mini: 8\nESP32-S3: 44\nESP32-S3 super mini: 48\nESP32-GENERIC: 2\n")
    argparser.add_argument('--boot-pin-on', '-bp-on', type=int, required=False, dest="pin_on", choices=[0, 1], default=0,
                           help="Value that indicate when boot pin led is ON.\nESP32-C3 super mini: 0\nESP32-S3: 0???\nESP32-GENERIC: 1\n")

    argparser.add_argument('--boot-wifi', type=str2bool, default=True,
                           help='Establish WiFi connection on boot')
    argparser.add_argument('--boot-lan', type=str2bool, default=False,
                           help='Establish LAN connection on boot')
    argparser.add_argument('--boot-webrepl', type=str2bool, default=True,
                           help='Start WEBREPL on boot')
    argparser.add_argument('--boot-time', type=str2bool, default=True,
                           help='Adjust CET/CEST time on boot')

    argparser.add_argument('--worker-name', '-w', type=str, help="Put the main.py with worker launcher.")
    argparser.add_argument('--port', '-p', type=str, required=False, default="/dev/ttyUSB0", help="Communication port.")
    argparser.add_argument('--commit', '-c', action="store_true",
                           help="Make a real attempt to transfer files to the device. Without that option nothing happens.")

    @classmethod
    def parse_args(cls, args=None):
        argcomplete.autocomplete(cls.argparser)
        return cls.argparser.parse_args(args)

    def __init__(self, parsed_args):
        self.worker_name = parsed_args.worker_name
        self.pin = parsed_args.pin
        self.pin_on = parsed_args.pin_on
        self.commit = parsed_args.commit
        self.port = parsed_args.port
        self.dest_board = parsed_args.dest_board
        self.dest_boot = parsed_args.dest_boot
        self.dest_main = parsed_args.dest_main
        self.boot_options = [parsed_args.boot_wifi, parsed_args.boot_lan, parsed_args.boot_webrepl,parsed_args.boot_time]

    def run(self):
        tempdir = tempfile.gettempdir()
        tempfile_prefix = "esp32_setup_{}_".format(uuid.uuid4())

        src_dir = os.path.dirname(os.path.dirname(os.path.normpath(__file__)))
        temp_files = []

        def create_temp_file(name: str) -> str:
            f = os.path.join(tempdir, f"{tempfile_prefix}{name}")
            temp_files.append(f)
            return f

        boot = create_temp_file("boot.py")
        with open(boot, "w") as f:
            f.write("from board.boot import Boot\n")
            f.write(f"boot = Boot.get_instance(pin_notify={self.pin}, pin_notify_on_signal={self.pin_on})\n")
            f.write("boot.load(wifi={}, lan={}, webrepl={}, time={})\n".format(*self.boot_options))
            # f.write("boot.setup_wifi()\n")
            # f.write("boot.setup_time()\n")

        if self.worker_name:
            worker_module = "{}".format(self.worker_name)
            worker_class = "{}Application".format(self.worker_name.capitalize())
            main = create_temp_file("main.py")
            with open(main, "w") as f:
                f.write(f"from {worker_module} import {worker_class}\n{worker_class}().run()\n")

        rshell = create_temp_file("rshell.py")
        with open(rshell, "w") as f:
            f.write("cp {} {}/\n".format(os.path.join(src_dir, "esp32/configuration.py"), self.dest_board))
            f.write("cp {} {}/\n".format(os.path.join(src_dir, "secrets.json"), self.dest_board))
            f.write("cp {} {}/\n".format(os.path.join(src_dir, "esp32/reboot.py"), self.dest_board))
            if self.worker_name:
                f.write("cp {} {}/{}\n".format(main, self.dest_board, self.dest_main))
                f.write("cp {} {}/\n".format(os.path.join(src_dir, "esp32/{}.py".format(worker_module)), self.dest_board))
            f.write("cp {} {}/{}\n".format(boot, self.dest_board, self.dest_boot))

        rshell_cmd = f"rshell -p {self.port} -f {{}}"

        print("BOOT ({}):".format(self.boot_options))
        print(open(boot).read())
        if self.worker_name:
            print("MAIN:")
            print(open(main).read())
        print("RSHELL: ({})".format(rshell_cmd.format(rshell)))
        print(open(rshell).read())

        try:
            if self.commit:
                os.system(rshell_cmd.format(rshell))
            else:
                print(" ************************************************************************************ ")
                print(" *                    THE BOARD IS NOT MODIFIED!                                    *")
                print(" * Use -c / --commit option to make a real attempt to transfer files to the device. *")
                print(" ************************************************************************************ ")
        finally:
            for f in temp_files:
                os.remove(f)


if __name__ == "__main__":
    Esp32Setup(Esp32Setup.parse_args()).run()

# print("DEBUG: {}".format(vars(args)))
# print("DEBUG: {}".format(args._get_args()))
# print("DEBUG: {}".format(dir(args)))
