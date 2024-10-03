import threading
import time

import sys

if len(sys.argv) != 2:
    print("USAGE: {} subsystem".format(__file__))
    raise SystemExit

system = sys.argv[1]

if system == "onair":

    from backend.onair import OnAir
    print("START OnAir")
    onAir = OnAir()
    thread = threading.Thread(target=onAir.start)
    thread.start()
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        onAir.stop()
        print("STOP OnAir")

elif system == "restapi":
    import uvicorn
    import socket
    from backend.restapi import app

    if socket.gethostname() == 'pi2':
        bind_to = '192.168.0.21'
    else:
        bind_to = 'localhost'

    uvicorn.run("backend.restapi:app", host=bind_to, port=8000, workers=1)

elif system == "charts":
    from backend.charts import ChartsGenerator
    try:
        ChartsGenerator().start()
    except KeyboardInterrupt:
        pass

else:
    print("Unknown subsystem: {}".format(system))
    raise SystemExit
