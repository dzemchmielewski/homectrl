"""
This module extends the native time functionalities with additional
helpers for date and time formatting, ISO date parsing, and
 millisecond-precision timestamps. It is designed for use in embedded
 and microcontroller environments, providing convenient utilities
 for handling time representations and conversions.
"""
import time
from utime import *
from micropython import const

_TS_YEAR = const(0)
_TS_MON = const(1)
_TS_MDAY = const(2)
_TS_HOUR = const(3)
_TS_MIN = const(4)
_TS_SEC = const(5)
_TS_WDAY = const(6)
_TS_YDAY = const(7)
_TS_ISDST = const(8)

_WDAY = const(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))
_MDAY = const(
    (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
)

_FMT = {
    "a": lambda dt: _WDAY[dt[_TS_WDAY]][:3],
    "A": lambda dt: _WDAY[dt[_TS_WDAY]],
    "b": lambda dt: _MDAY[dt[_TS_MON] - 1][:3],
    "B": lambda dt: _MDAY[dt[_TS_MON] - 1],
    "d": lambda dt: "%02d" % dt[_TS_MDAY],
    "e": lambda dt: "%01d" % dt[_TS_MDAY],
    "H": lambda dt: "%02d" % dt[_TS_HOUR],
    "I": lambda dt: "%02d" % (dt[_TS_HOUR] % 12),
    "j": lambda dt: "%03d" % dt[_TS_YDAY],
    "k": lambda dt: "%01d" % dt[_TS_YDAY],
    "m": lambda dt: "%02d" % dt[_TS_MON],
    "n": lambda dt: "%01d" % dt[_TS_MON],
    "M": lambda dt: "%02d" % dt[_TS_MIN],
    "P": lambda dt: "AM" if dt[_TS_HOUR] < 12 else "PM",
    "S": lambda dt: "%02d" % dt[_TS_SEC],
    "w": lambda dt: str(dt[_TS_WDAY]),
    "y": lambda dt: "%02d" % (dt[_TS_YEAR] % 100),
    "Y": lambda dt: str(dt[_TS_YEAR]),
}

def time_ms() -> int:
    return time() * 1000 + (ticks_ms() % 1000)

def strftime(fmt: str, dt: tuple|int) -> str:
    """
    Formats a date/time tuple according to the given format string.
    Supported format codes:
        %a - Abbreviated weekday name (e.g., Mon)
        %A - Full weekday name (e.g., Monday)
        %b - Abbreviated month name (e.g., Jan)
        %B - Full month name (e.g., January)
        %d - Day of the month as zero-padded decimal (01-31)
        %d - Day of the month as decimal (1-31)
        %H - Hour (24-hour clock) as zero-padded decimal (00-23)
        %I - Hour (12-hour clock) as zero-padded decimal (01-12)
        %j - Day of the year as zero-padded decimal (001-366)
        %k - Day of the year as decimal (1-366)
        %m - Month as zero-padded decimal (01-12)
        %n - Month as decimal (1-12)
        %M - Minute as zero-padded decimal (00-59)
        %P - AM or PM
        %S - Second as zero-padded decimal (00-59)
        %w - Weekday as decimal (0=Monday)
        %y - Year without century as zero-padded decimal (00-99)
        %Y - Year with century as decimal

    Args:
        fmt: Format string using supported codes.
        dt:  Time tuple as returned by localtime() OR int - number of seconds since epoch.

    Returns:
        Formatted date/time string.
    """
    if type(dt) == int:
        dt = time.localtime(dt)

    out = []
    esc = False

    for ch in fmt:
        if esc:
            fn = _FMT.get(ch)
            out.append(fn(dt) if fn else ch)
            esc = False
        elif ch == "%":
            esc = True
        else:
            out.append(ch)

    return "".join(out)


def fromisostrict(s: str) -> int:
    """
    Parses a strict ISO date or datetime string and returns a timestamp (seconds since epoch).

    Supported formats:
        - YYYY-MM-DD
        - YYYY-MM-DDThh:mm:ss

    Args:
        s: ISO date or datetime string.

    Returns:
        int: Timestamp (seconds since epoch).

    Raises:
        ValueError: If the input string does not match the supported formats or contains invalid date/time values.
    """
    try:
        if len(s) == 10:
            # YYYY-MM-DD
            if s[4] != '-' or s[7] != '-':
                raise ValueError
            return mktime((int(s[0:4]), int(s[5:7]), int(s[8:10]), 0, 0, 0, 0, 0))

        elif len(s) == 19 or (len(s) == 20 and s[19] == 'Z'):
            # YYYY-MM-DDThh:mm:ss
            if s[4] != '-' or s[7] != '-' or s[10] != 'T' or s[13] != ':' or s[16] != ':':
                raise ValueError
            return mktime((int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19]), 0, 0))

        else:
            raise ValueError

    except (ValueError, IndexError):
        raise ValueError("Invalid date format. Expected 'YYYY-MM-DD' or 'YYYY-MM-DDThh:mm:ss'.")

def last_weekday_of_month(year: int, month: int, weekday: int) -> int:
    """
    Returns the day-of-month of the last occurrence of a given weekday in a month.

    Args:
        year:    Full year (e.g. 2024).
        month:   Month number (1-12).
        weekday: Target weekday, 0=Monday .. 6=Sunday (same convention as gmtime).

    Returns:
        Day of month (1-31) of the last matching weekday.
    """

    # first day of next month
    if month == 12:
        ts = mktime((year + 1, 1, 1, 0, 0, 0, 0, 0, 0))
    else:
        ts = mktime((year, month + 1, 1, 0, 0, 0, 0, 0, 0))

    # step back one day → last day of requested month
    ts -= 86400

    t = gmtime(ts)
    last_day = t[2]
    wday = t[6]

    return last_day - ((wday - weekday) % 7)

def utc_to_local(utc: tuple | int) -> tuple | int:
    """Convert UTC to local time (CET/CEST), accounting for DST.

    Accepts either a Unix timestamp (int) or a time tuple (as returned by
    gmtime/localtime) and returns the same type.  The DST boundaries follow
    the EU rule: clocks spring forward on the last Sunday of March at 01:00
    UTC, and fall back on the last Sunday of October at 01:00 UTC.
    """
    ts = utc if type(utc) == int else mktime(utc)
    year = gmtime(ts)[0]
    hh_march   = mktime((year, 3,  (31 - (int(5 * year // 4 + 4)) % 7), 1, 0, 0, 0, 0, 0))
    hh_october = mktime((year, 10, (31 - (int(5 * year // 4 + 1)) % 7), 1, 0, 0, 0, 0, 0))
    if ts < hh_march:
        result = ts + 3600   # CET:  UTC+1H
    elif ts < hh_october:
        result = ts + 7200   # CEST: UTC+2H
    else:
        result = ts + 3600   # CET:  UTC+1H
    return result if type(utc) == int else localtime(result)

def local_to_utc(local: tuple | int) -> tuple | int:
    """Convert local time (CET/CEST) to UTC, accounting for DST.

    Accepts either a Unix timestamp (int) or a time tuple (as returned by
    gmtime/localtime) and returns the same type.  Inverse of utc_to_local;
    round-tripping via local_to_utc(utc_to_local(ts)) preserves ts.
    """
    ts = local if type(local) == int else mktime(local)
    year = gmtime(ts)[0]
    hh_march   = mktime((year, 3,  (31 - (int(5 * year // 4 + 4)) % 7), 1, 0, 0, 0, 0, 0))
    hh_october = mktime((year, 10, (31 - (int(5 * year // 4 + 1)) % 7), 1, 0, 0, 0, 0, 0))
    if ts < hh_march + 3600:
        result = ts - 3600   # CET:  UTC+1H
    elif ts < hh_october + 3600:
        result = ts - 7200   # CEST: UTC+2H
    else:
        result = ts - 3600   # CET:  UTC+1H
    return result if type(local) == int else gmtime(result)
