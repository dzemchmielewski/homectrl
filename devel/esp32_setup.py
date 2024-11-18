#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import os
import tempfile
import uuid
import argparse, argcomplete


class Esp32Setup:

    argparser = argparse.ArgumentParser(
        prog='esp32setup',
        description='DZEM HomeCtrl Devel - ESP32 board setup',
        add_help=True, formatter_class=argparse.RawTextHelpFormatter)
    argparser.add_argument('--boot-pin', '-bp', type=int, required=False, dest="pin",
                           help="Pin number to use for boot notification.\nESP32-C3 super mini: 8\nESP32???: 2")
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
        self.commit = parsed_args.commit
        self.port = parsed_args.port

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
            f.write(f"boot = Boot.get_instance(pin_notify={self.pin})\n")
            f.write("boot.load()\n")
            # f.write("boot.setup_wifi()\n")
            # f.write("boot.setup_time()\n")

        if self.worker_name:
            worker_module = "{}_worker".format(self.worker_name)
            worker_class = "{}Worker".format(self.worker_name.capitalize())
            main = create_temp_file("main.py")
            with open(main, "w") as f:
                f.write(f"from {worker_module} import {worker_class}\nboot.start_server({worker_class}())\n")

        rshell = create_temp_file("rshell.py")
        with open(rshell, "w") as f:
            f.write("cp {} /board/\n".format(os.path.join(src_dir, "board/configuration.py")))
            f.write("cp {} /board/\n".format(os.path.join(src_dir, "secrets.json")))
            f.write("cp {} /board/\n".format(os.path.join(src_dir, "esp32/reboot.py")))
            if self.worker_name:
                f.write("cp {} /board/main.py\n".format(main))
                f.write("cp {} /board/\n".format(os.path.join(src_dir, "esp32/{}.py".format(worker_module))))
            f.write("cp {} /board/boot.py\n".format(boot))

        rshell_cmd = f"rshell -p {self.port} -f {{}}"

        print("BOOT:")
        print(open(boot).read())
        if self.worker_name:
            print("MAIN:")
            print(open(main).read())
        print("RSHELL: ({})".format(rshell_cmd.format(rshell)))
        print(open(rshell).read())

        try :
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

