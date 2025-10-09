#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse, argcomplete
import logging
import threading
import time

services = ["onair", "restapi", "charts", "weather"]

parser = argparse.ArgumentParser(description="HomeCtrl service launcher", add_help=True)
parser.add_argument("service",  choices=services, help="Backend service to start")
argcomplete.autocomplete(parser)
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


system = args.service

if system == "onair":

    from backend.onair import OnAir
    from backend.activities import Activities

    threads = []
    print("Starting OnAir...")
    onAir = OnAir()
    activities = Activities()
    threads.append(threading.Thread(target=onAir.start))
    threads.append(threading.Thread(target=activities.start))

    for t in threads:
        t.start()
    print("Started OnAir")

    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        pass

    print("Stopping OnAir...")
    onAir.stop()
    activities.stop()
    for t in threads:
        if t.is_alive():
            t.join()
    print("Stopped OnAir")


elif system == "restapi":
    import uvicorn
    import socket
    from backend.restapi import app

    if socket.gethostname() == 'pi':
        bind_to = '192.168.0.24'
    else:
        bind_to = 'localhost'

    uvicorn.run("backend.restapi:app", host=bind_to, port=8000, workers=1)

elif system == "charts":
    from backend.charts import ChartsGenerator
    try:
        ChartsGenerator().start()
    except KeyboardInterrupt:
        pass

elif system == "weather":
    from backend.weather import Weather
    try:
        Weather().start()
    except KeyboardInterrupt:
        pass

else:
    print("Unknown subsystem: {}".format(system))
    raise SystemExit
