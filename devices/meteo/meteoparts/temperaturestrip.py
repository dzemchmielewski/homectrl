from colors import Colors
from plot import LinePlot, Plot

from meteoparts.daychartstrip import DayChartStrip

from toolbox.framebufext import FrameBufferFont

import logging
logger = logging.getLogger(__name__)

class TemperatureStrip(DayChartStrip):

    def begin_draw(self, font: FrameBufferFont, max_y: float, min_y: float) -> Plot:
        plot = LinePlot(self.colors.map, font)

        # Round max_y and min_y to nearest multiple of 5
        plot.axis_y_max = ((int(max_y) + 4) // 5) * 5
        plot.axis_y_min = ((int(min_y) - 4) // 5) * 5

        vertical_ticks = abs(plot.axis_y_max) // 5 + abs(plot.axis_y_min) // 5

        plot.margins(bottom=15)
        plot.ticks_count(bottom=25, top=25, left=vertical_ticks + 1)
        plot.ticks_per_label(bottom=4, left=1)
        plot.dot_size = 2
        plot.signals_size = 4

        plot.grid_dash(None, (3, 2))
        plot.ticks_labels_list(bottom = ["0", "4", "8", "12", "16", "20"], left = [num for num in range(plot.axis_y_min, plot.axis_y_max + 1, 5)])
        plot.label_format = lambda x : (" °C" if x == plot.axis_y_max else "") + f"{x}"
        return plot

    def end_past_draw(self, plot: Plot) -> Plot:
        plot.ticks_labels(left=False)  # no labels for next charts
        return plot

    def begin_frsct_draw(self, plot: Plot) -> Plot:
        plot.grid_count(0, 0)
        plot.colormap = plot.colormap | {
            'line': self.colors.DARK,
            'dot': self.colors.DARK,
        }
        return plot

    def end_frsct_draw(self, plot: Plot, penult: bool = False) -> Plot:
        plot.grid_count_vert = None
        plot.grid_count_horiz = None
        return plot



