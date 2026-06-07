from colors import Colors
from plot import Plot, BarPlot

from meteoparts.daychartstrip import DayChartStrip

from toolbox.framebufext import FrameBufferFont

import logging
logger = logging.getLogger(__name__)

class DayLightStrip:

    def __init__(self, colors: Colors):
        self.colors = colors

    def h48plot(self, font: FrameBufferFont, max_y: float, min_y: float, h_start: int, h_count: int) -> Plot:
        plot = BarPlot(self.colors.map, font)
        plot.margins(bottom=15)
        plot.axes(left=False, bottom=False, right=False, top=False)

        plot.axis_y_max = 1
        plot.axis_y_min = 0
        plot.colormap['bars'] = self.colors.LIGHT
        plot.grid_count(0, 0)
        plot.ticks_labels(right=False, left=False, top=False, bottom=False)
        return plot

