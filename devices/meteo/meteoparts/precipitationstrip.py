from colors import Colors
from plot import BarPlot, Plot

from meteoparts.daychartstrip import DayChartStrip

from toolbox.framebufext import FrameBufferFont

class PrecipitationStrip(DayChartStrip):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_y = None

    def begin_draw(self, font: FrameBufferFont, max_y: float, min_y: float) -> Plot:
        plot = BarPlot(self.colors.map, font)
        plot.margins(bottom=15)
        plot.axes(left=False, bottom=False, right=False, top=False)

        max_y = max(max_y, 2)
        plot.axis_y_max = int(max_y) if max_y == int(max_y) else int(max_y) + 1
        plot.axis_y_min = 0
        plot.colormap['bars'] = self.colors.LIGHT
        plot.grid_count(0, 0)
        plot.ticks_labels(right=False, left=False, top=False, bottom=False)

        plot.colormap = plot.colormap | {'bars': self.colors.DARK}
        return plot

    def end_past_draw(self, plot: Plot) -> Plot:
        return plot

    def begin_frsct_draw(self, plot: Plot) -> Plot:
        plot.colormap = plot.colormap | {'bars': self.colors.LIGHT}
        return plot

    def end_frsct_draw(self, plot: Plot, penult: bool = False) -> Plot:
        if penult:
            plot.ticks_per_label(right=1)
            plot.ticks_count(right=plot.axis_y_max + 1)
            plot.ticks_labels(right=True)
            plot.ticks_length(right=3)
            plot.axes(right=True)
            plot.label_format = lambda x : f"{int(x)}" + ("mm" if x == plot.axis_y_max else "")
        return plot
