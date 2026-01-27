import time
import logging

from plot import Plot
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset

logger = logging.getLogger(__name__)

class DayChartStrip:

    def __init__(self, astro: dict, colors: Colors):
        self.colors = colors
        # self.days_count = len(astro['astro'])
        self.days_count = 3
        self.start_day = min(astro['astro'], key=lambda i: i['day']['day_offset'])['day']['date']
        logger.debug(f"Start Date: {self.start_day}, Days count: {self.days_count}")

    @staticmethod
    def split_by_days(data, start_date):
        sy, sm, sd, sh = time.localtime(time.fromisostrict(start_date))[0:4]
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
        sy, sm, sd, sh = time.localtime(time.fromisostrict(start_date))[0:4]
        ty, tm, td, th  = time.localtime(time.fromisostrict(cut_date))[0:4]
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

    @staticmethod
    def _add_hours(date_ymd: str, hours: int) -> str:
        y, m, d  = int(date_ymd[0:4]), int(date_ymd[5:7]), int(date_ymd[8:10])
        lt = time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0)) + (hours * 60 * 60))
        return "%04d-%02d-%02dT%02d:00:00" % (lt[0], lt[1], lt[2], lt[3])

    def begin_draw(self, font: FrameBufferFont, max_y: float) -> Plot:
        raise NotImplementedError()

    def end_past_draw(self, plot: Plot) -> Plot:
        raise NotImplementedError()

    def begin_frsct_draw(self, plot: Plot) -> Plot:
        raise NotImplementedError()

    def end_frsct_draw(self, plot: Plot) -> Plot:
        raise NotImplementedError()

    def range(self, list_of_list) -> tuple:
        max_y, min_y = None, None
        for ys in list_of_list:
            max_y = max(max_y, max(ys) if len(ys) > 0 else 0) if max_y is not None else (max(ys) if len(ys) > 0 else 0)
            min_y = min(min_y, min(ys) if len(ys) > 0 else 0) if min_y is not None else (min(ys) if len(ys) > 0 else 0)
        return max_y, min_y

    def draw(self, fb: FrameBufferExtension, font: FrameBufferFont,
             past_start_date: str, past: list,
             future_start_date: str, future: list):

        logger.debug(f"PAST/FUTURE start dates: {past_start_date} / {future_start_date}")
        past_values = self.split_by_days(self.cut_before(past, past_start_date, self.start_day), self.start_day)
        logger.debug(f"PAST (len={len(past_values)}): {past_values}")

        frcst_cut_date = self._add_hours(self.start_day, sum(len(day) for day in past_values))
        frcst_values = self.split_by_days(self.cut_before(future, future_start_date, frcst_cut_date), frcst_cut_date)
        logger.debug(f"FRCST cut date: {frcst_cut_date}")
        logger.debug(f"FRCST (len={len(frcst_values)}): {frcst_values}")

        x, y, width, height = 0, 0, fb.width // self.days_count, fb.height
        max_y, min_y = self.range(past_values)
        _max_y, _min_y = self.range(frcst_values)
        max_y, min_y = self.ceil(max(max_y, _max_y)), self.ceil(min(min_y, _min_y))

        plot = self.begin_draw(font, max_y, min_y)
        logger.debug(f"MAX/MIN VALUE: {plot.axis_y_max}, {plot.axis_y_min}")

        # PAST values:
        for i in range(len(past_values)):
            ys = past_values[i]
            # # Fill missing precipitation values with 0:
            if 0 < len(ys) < 24:
                ys = ys + ([0] * (24-len(ys)))
            logger.debug(f"PAST {i}, data: {ys}")
            plot.draw(FrameBufferOffset(fb, x, y, width, height), None, ys)
            x += width - 2
            self.end_past_draw(plot)

        # FRCST values:
        self.begin_frsct_draw(plot)
        # back to previous plot, to draw future values on it
        x -= width - 2

        for i in range(len(past_values) - 1, self.days_count):
            idx = i - len(past_values) + 1
            ys = frcst_values[idx] if idx < len(frcst_values) else []
            if 0 < len(ys) < 24:
                if idx == 0:
                    # The day where PAST and FUTURE meet - pad at the beginning
                    ys = ([0] * (24-len(ys))) + ys
                else:
                    # Other FUTURE days - pad at the end
                    ys = ys + ([0] * (24-len(ys)))
            logger.debug(f"FRCST {idx}, data: {ys}")
            plot.draw(FrameBufferOffset(fb, x, y, width, height), None, ys)
            self.end_frsct_draw(plot)
            x = x + width - 2

