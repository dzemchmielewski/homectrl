#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse, argcomplete
import logging
import time

services = ["onair", "restapi", "charts", "devel"]

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

    logging.info("Starting OnAir...")
    onAir = OnAir()
    try:
        onAir.start()
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logging.info("Stopping OnAir...")
        onAir.stop()
        logging.info("Stopped OnAir")


elif system == "restapi":
    import uvicorn
    import socket
    from backend.restapi import app, UVICORN_LOG_CONFIG

    if socket.gethostname() == 'pi':
        bind_to = '192.168.0.24'
    else:
        bind_to = 'localhost'

    uvicorn.run("backend.restapi:app", host=bind_to, port=8000, workers=1, log_config=UVICORN_LOG_CONFIG)

elif system == "charts":
    from backend.charts import ChartsGenerator
    try:
        ChartsGenerator().start()
    except KeyboardInterrupt:
        pass

elif system == "devel":
    # put your devel code here
    # that will run with proper python environment
    from backend.services.astro import Astro
    astro_service = Astro()
    # astro_service.mqtt.publish = lambda topic, message, retain: print(f"Mock publish to {topic}: {message} (retain={retain})")
    astro_service.start()
    pass

else:
    print("Unknown subsystem: {}".format(system))
    raise SystemExit
