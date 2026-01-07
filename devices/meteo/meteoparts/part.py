import time

class Part:

    @staticmethod
    def parse_iso(s):
        # "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD"
        y = int(s[0:4])
        m = int(s[5:7])
        d = int(s[8:10])
        h = int(s[11:13]) if 'T' in s else 0
        return y, m, d, h

    @staticmethod
    def split_by_days(data, start_date):
        sy, sm, sd, sh = Part.parse_iso(start_date)
        result = []
        i, n = 0, len(data)

        # first day (may be partial)
        first_len = min(24 - sh, n)
        if first_len > 0:
            result.append(data[0:first_len])
            i = first_len

        # full days
        while i < n:
            result.append(data[i:i+24])
            i += 24

        return result

    @staticmethod
    def cut_before(data: list, start_date: str, cut_date: str) -> list:
        sy, sm, sd, sh = Part.parse_iso(start_date)
        ty, tm, td, th  = Part.parse_iso(cut_date)
        t_start = time.mktime((sy, sm, sd, sh, 0, 0, 0, 0))
        t_target = time.mktime((ty, tm, td, th, 0, 0, 0, 0))
        index = 0 if t_start > t_target else (t_target - t_start) // 3600

        # remove last None values:
        while len(data) > 0 and data[-1] is None:
            data.pop()

        return data[index:]

    @staticmethod
    def ceil(x):
        i = int(x)
        return i if x <= i else i + 1

