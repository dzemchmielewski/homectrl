import logging
import time

from colors import Colors
from plot import BarPlot

from meteoparts.part import Part
from toolbox.framebufext import FrameBufferExtension, FrameBufferOffset, FrameBufferFont

logger = logging.getLogger(__name__)

class PrecipitationPart(Part):

    def __init__(self, astro: dict, colors: Colors):
        self.astro = astro
        self.colors = colors
        self.days_count = len(self.astro['astro'])

    @staticmethod
    def _add_hours(date_ymd: str, hours: int) -> str:
        y, m, d  = int(date_ymd[0:4]), int(date_ymd[5:7]), int(date_ymd[8:10])
        lt = time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0)) + (hours * 60 * 60))
        return "%04d-%02d-%02dT%02d:00:00" % (lt[0], lt[1], lt[2], lt[3])

    def draw(self, fb: FrameBufferExtension, font: FrameBufferFont,
             past_start_date: str, past: list,
             future_start_date: str, future: list):

        logger.debug(f"PAST/FUTURE start dates: {past_start_date} / {future_start_date}")

        start_day = min(self.astro['astro'], key=lambda i: i['day']['day_offset'])['day']['date']
        past_values = self.split_by_days(self.cut_before(past, past_start_date, start_day), start_day)
        logger.debug(f"PAST cut date: {start_day}")
        logger.debug(f"Precipitation PAST (len={len(past_values)}): {past_values}")

        frcst_cut_date = self._add_hours(start_day, sum(len(day) for day in past_values))
        frcst_values = self.split_by_days(self.cut_before(future, future_start_date, frcst_cut_date), frcst_cut_date)
        logger.debug(f"FRCST cut date: {frcst_cut_date}")
        logger.debug(f"Precipitation FRCST (len={len(frcst_values)}): {frcst_values}")

        x, y, width, height = 0, 0, fb.width // self.days_count, fb.height

        # Find max precipitation value to set Y axis max:
        max_precipitation = 0
        for ys in past_values:
            max_precipitation = max(max_precipitation, max(ys) if len(ys) > 0 else 0)
        for ys in frcst_values:
            max_precipitation = max(max_precipitation, max(ys) if len(ys) > 0 else 0)
        max_precipitation = max(3, self.ceil(max_precipitation))
        logger.debug(f"MAX: {max_precipitation}")

        plot = BarPlot(self.colors.map, font)
        plot.margins(bottom=15)
        plot.axis_y_max = max_precipitation
        # plot.ticks_count(bottom=7, left=max_precipitation + 1)
        plot.ticks_count(bottom=25, left=max_precipitation + 1)
        plot.ticks_per_label(bottom=4, left=1)

        plot.grid_dash(None, (3, 2))
        plot.ticks_labels_list(bottom = ["0", "4", "8", "12", "16", "20"], left = [i for i in range(max_precipitation + 1)])

        # PAST values:
        for i in range(len(past_values)):
            ys = past_values[i]
            # # Fill missing precipitation values with 0:
            if 0 < len(ys) < 24:
                ys = ys + ([0] * (24-len(ys)))
            logger.debug(f"Precipitation PAST {i}, data: {ys}")
            plot.draw(FrameBufferOffset(fb, x, y, width, height), None, ys)
            x += width - 1
            plot.ticks_labels(left=False)  # no labels for next charts

        # FRCST values:
        plot.colormap['bars'] = self.colors.LIGHT
        plot.grid_count(0, 0)
        # back to previous plot, to draw future values on it
        x -= width - 1

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
            logger.debug(f"Precipitation FRCST {idx}, data: {ys}")
            plot.draw(FrameBufferOffset(fb, x, y, width, height), None, ys)
            plot.grid_count_vert = None
            plot.grid_count_horiz = None
            x = x + width - 1

