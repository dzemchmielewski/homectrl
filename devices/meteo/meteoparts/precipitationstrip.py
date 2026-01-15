from colors import Colors
from plot import BarPlot, Plot

from meteoparts.daychartstrip import DayChartStrip

from toolbox.framebufext import FrameBufferFont

class PrecipitationStrip(DayChartStrip):

    def begin_draw(self, font: FrameBufferFont, max_y: float, min_y: float) -> Plot:
        plot = BarPlot(self.colors.map, font)
        plot.margins(bottom=15)
        # plot.ticks_count(bottom=7, left=max_y + 1)
        plot.ticks_count(bottom=25, left=max_y + 1)
        plot.ticks_per_label(bottom=4, left=1)
        plot.axis_y_max = max_y
        plot.axis_y_min = 0

        plot.grid_dash(None, (3, 2))
        plot.ticks_labels_list(bottom = ["0", "4", "8", "12", "16", "20"], left = [i for i in range(max_y + 1)])
        return plot

    def end_past_draw(self, plot: Plot) -> Plot:
        plot.ticks_labels(left=False)  # no labels for next charts
        return plot

    def begin_frsct_draw(self, plot: Plot) -> Plot:
        plot.colormap['bars'] = self.colors.LIGHT
        plot.grid_count(0, 0)

    def end_frsct_draw(self, plot: Plot) -> Plot:
        plot.grid_count_vert = None
        plot.grid_count_horiz = None

    def max_value(self):
        return 3

    def min_value(self):
        return 0
