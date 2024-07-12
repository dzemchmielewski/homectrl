from datetime import datetime
import time


def log_entry_prefix():
    return "{:%Y-%m-%d %H:%M:%S.%f}".format(datetime.now())


def time_ms():
    return int(round(time.time() * 1000))
