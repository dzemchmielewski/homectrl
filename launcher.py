import threading
import time

import sys

if len(sys.argv) != 2:
    print("USAGE: {} subsystem".format(__file__))
    raise SystemExit

system = sys.argv[1]

if system == "onair":

    from backend.onair import OnAir
    from backend.activities import Activities, Database2MQTT

    threads = []
    print("Starting OnAir...")
    onAir = OnAir()
    activities = Activities()
    # threads.append(threading.Thread(target=onAir.start))
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

# elif system == "temp":
#     from backend.activities import Database2MQTT
#     Database2MQTT().run()

else:
    print("Unknown subsystem: {}".format(system))
    raise SystemExit
