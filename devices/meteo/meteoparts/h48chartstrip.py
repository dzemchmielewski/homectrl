import logging
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset

logger = logging.getLogger(__name__)

class H48ChartStrip:

    HOURS_COUNT = 36

    def __init__(self,  colors: Colors, provider):
        self.colors = colors
        self.provider = provider

    def debug(self, align: int, message: str):
        logger.debug(f"{' '*2*align}{message}")
    def info(self, align: int, message: str):
        logger.info(f"{' '*2*align}{message}")

    def draw(self, fb: FrameBufferExtension, font: FrameBufferFont, start_date: str, forecast: list):
        logalign = 0
        h_start = int(start_date[11:13])
        self.debug(logalign, f"H48FRCST. Start date: {start_date}, H start: {h_start}, Hours: {self.HOURS_COUNT}")
        logalign += 1

        x, y, width, height = 0, 0, fb.width, fb.height
        max_y, min_y = None, None
        ys = [y for y in forecast if y is not None]
        max_y = max(max_y, max(ys) if len(ys) > 0 else 0) if max_y is not None else (max(ys) if len(ys) > 0 else 0)
        min_y = min(min_y, min(ys) if len(ys) > 0 else 0) if min_y is not None else (min(ys) if len(ys) > 0 else 0)
        self.debug(logalign,"MAX/MIN RANGE VALUES: {}, {}".format(max_y, min_y))

        plot = self.provider.h48plot(font, max_y, min_y, h_start, self.HOURS_COUNT)
        self.debug(logalign,f"MAX/MIN VALUE: {plot.axis_y_max}, {plot.axis_y_min}")

        plot.draw(FrameBufferOffset(fb, x, y, width, height), None, forecast[0:self.HOURS_COUNT])
        x += width - 2


        logalign -= 1
        self.debug(logalign, f"H48FRCST completed.")

