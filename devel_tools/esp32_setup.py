#!/usr/bin/env python
import os
import tempfile
import uuid

worker_name = "dev"
led_notify = "True"
rshell_cmd = "rshell -p /dev/ttyACM0 -f {}"

worker_module = "{}_worker".format(worker_name)
worker_class = "{}Worker".format(worker_name.capitalize())

uuid = uuid.uuid4()
tempdir = tempfile.gettempdir()
tempfile_prefix = "esp32_setup_{}_".format(uuid)

src_dir = os.path.dirname(os.path.dirname(__file__))

temp_files = []


def create_temp_file(name: str) -> str:
    f = os.path.join(tempdir, f"{tempfile_prefix}{name}")
    temp_files.append(f)
    return f


boot = create_temp_file("boot.py")
with open(boot, "w") as f:
    f.write("from board.boot import Boot\n")
    f.write(f"boot = Boot.get_instance(led_notify={led_notify})\n")
    f.write("boot.load()\n")

main = create_temp_file("main.py")
with open(main, "w") as f:
    f.write(f"from {worker_module} import {worker_class}\nboot.start_server({worker_class}())\n")

rshell = create_temp_file("rshell.py")
with open(rshell, "w") as f:
    f.write("cp {} /board/main.py\n".format(main))
    f.write("cp {} /board/\n".format(os.path.join(src_dir, "board/configuration.py")))
    f.write("cp {} /board/\n".format(os.path.join(src_dir, "secrets.json")))
    f.write("cp {} /board/\n".format(os.path.join(src_dir, "esp32/reboot.py")))
    f.write("cp {} /board/\n".format(os.path.join(src_dir, "esp32/{}.py".format(worker_module))))
    f.write("cp {} /board/boot.py\n".format(boot))

os.system(rshell_cmd.format(rshell))

for f in temp_files:
    os.remove(f)
