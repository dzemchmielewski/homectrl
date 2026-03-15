import time

def sys_to_rtc(rtc_write_func):
    try:
        dt = time.local_to_utc(time.localtime())
        rtc_write_func(dt)
        print(f"Time saved: {dt}")
        return True
    except:
        return False

def rtc_to_sys(rtc_read_func):
    from machine import RTC
    try:
        (year, month, mday, hour, minute, second, weekday, yearday) = (
            time.utc_to_local(rtc_read_func()))
        RTC().datetime((year, month, mday, 0, hour, minute, second, 0))
        print(f"Time loaded: {time.localtime()}")
        return True
    except:
        return False

def ntp_to_sys(ntphost: str = None):
    import ntptime
    from machine import RTC
    if ntphost:
        ntptime.host = ntphost
    cet = time.localtime(time.utc_to_local(ntptime.time()))
    (year, month, mday, hour, minute, second, weekday, yearday) = cet
    RTC().datetime((year, month, mday, 0, hour, minute, second, 0))
    print(f"Time loaded: {time.localtime()}")

