import logging

from colors import Colors
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset

logger = logging.getLogger(__name__)


TICK_BELOW = 0
TICK_CENTER = 1
TICK_ABOVE = 2
TICK_LEFT = 0
TICK_RIGHT = 2


class Plot:

    def __init__(self, color: Colors, font: FrameBufferFont):
        self.color = color
        for key in ['axis', 'grid', 'bars', 'frame', 'labels']:
            if key not in self.color.map:
                raise Exception(f'Color key "{key}" not found in color map: {self.color.map.keys()}')
        if 'ticks' not in self.color.map:
            self.color.map['ticks'] = self.color.map['axis']
        if 'labels' not in self.color.map:
            self.color.map['labels'] = self.color.map['axis']

        self.font = font
        self.frame = False  # draw frame around chart

        # self.axes(tuple[bool, bool]) OR:
        self.axis_x = True  # draw X axis
        self.axis_y = True  # draw Y axis

        self.axis_y_min = 0
        self.axis_y_max = 5

        self.margin_left = 10  # left margin for Y axis
        self.margin_bottom = 5  # bottom margin for X axis

        # self.grid_dash(tuple[int, int] | None) OR:
        self.grid_x_dash = (1, 5)  # grid's on/off segments ; None = no grid
        self.grid_y_dash = (1, 5)  # grid's on/off segments ; None = no grid

        # self.grid_count(tuple[int, int] | None) OR:
        self.grid_x_count = None  # number of vertical grid lines; if None, align with ticks_x_count or auto generate
        self.grid_y_count = None  # number of horizontal grid lines; if None, align with ticks_y_count or auto generate

        # self.ticks_length(tuple[int, int]) OR:
        self.ticks_x_length = 3  # length of X ticks; if None or 0, no ticks
        self.ticks_y_length = 3  # length of Y ticks; if None or 0, no ticks

        # self.ticks_pos(tuple[int, int]) OR:
        self.ticks_x_pos = TICK_BELOW  # position of X ticks
        self.ticks_y_pos = TICK_LEFT  # position of Y ticks

        # self.ticks_count(tuple[int, int] | None) OR:
        self.ticks_x_count = None  # number of X ticks; if None, align with grid_x_count or auto generate
        self.ticks_y_count = None  # number of Y ticks; if None, align with grid_y_count or auto generate

        # self.ticks_labels(tuple[list, list] | None) OR:
        self.ticks_x_labels = None # X ticks labels; if None, auto generate
        self.ticks_y_labels = None  # Y ticks labels; if None, auto generate

        # self.ticks_per_label(tuple[int, int]):
        self.ticks_x_per_label = 1  # number of X ticks per label
        self.ticks_y_per_label = 1  # number of Y ticks per label

    @property
    def grid_dash(self):
        return self.grid_x_dash, self.grid_y_dash
    @grid_dash.setter
    def grid_dash(self, dash):
        if not isinstance(dash, tuple) or len(dash) != 2:
            raise ValueError("dash must be a tuple like ((on, off) | None, (on, off) | None)")
        for d in dash:
            if d is not None:
                if not isinstance(d, tuple) or len(d) != 2:
                    raise ValueError("dash elements must be tuple like (on, off) or None")
        self.grid_x_dash, self.grid_y_dash = dash

    @property
    def axis(self):
        return self.axis_x, self.axis_y
    @axis.setter
    def axis(self, axes: tuple):
        if not isinstance(axes, tuple) or len(axes) != 2:
            raise ValueError("axes must be a tuple like (axis_x, axis_y)")
        self.axis_x, self.axis_y = axes

    @property
    def grid_count(self):
        return self.grid_x_count, self.grid_y_count
    @grid_count.setter
    def grid_count(self, counts: tuple):
        if not isinstance(counts, tuple) or len(counts) != 2:
            raise ValueError("counts must be a tuple like (x_count, y_count)")
        self.grid_x_count, self.grid_y_count = counts

    @property
    def tickes_length(self):
        return self.ticks_x_length, self.ticks_y_length
    @tickes_length.setter
    def tickes_length(self, lengths: tuple):
        if not isinstance(lengths, tuple) or len(lengths) != 2:
            raise ValueError("lengths must be a tuple like (x_length, y_length)")
        self.ticks_x_length, self.ticks_y_length = lengths

    @property
    def ticks_pos(self):
        return self.ticks_x_pos, self.ticks_y_pos
    @ticks_pos.setter
    def ticks_pos(self, positions: tuple):
        if not isinstance(positions, tuple) or len(positions) != 2:
            raise ValueError("positions must be a tuple like (x_pos, y_pos)")
        self.ticks_x_pos, self.ticks_y_pos = positions

    @property
    def ticks_count(self):
        return self.ticks_x_count, self.ticks_y_count
    @ticks_count.setter
    def ticks_count(self, counts: tuple):
        if counts is not None:
            if not isinstance(counts, tuple) or len(counts) != 2:
                raise ValueError("counts must be a tuple like (x_count, y_count)")
            self.ticks_x_count, self.ticks_y_count = counts
        else :
            self.ticks_x_count, self.ticks_y_count = None, None

    @property
    def ticks_per_label(self):
        return self.ticks_x_per_label, self.ticks_y_per_label
    @ticks_per_label.setter
    def ticks_per_label(self, counts: tuple):
        if not isinstance(counts, tuple) or len(counts) != 2:
            raise ValueError("counts must be a tuple like (x_count, y_count)")
        self.ticks_x_per_label, self.ticks_y_per_label = counts

    @property
    def ticks_labels(self):
        return self.ticks_x_labels, self.ticks_y_labels
    @ticks_labels.setter
    def ticks_labels(self, labels: tuple):
        if labels is not None:
            if not isinstance(labels, tuple) or len(labels) != 2:
                raise ValueError("labels must be a tuple like (x_labels, y_labels)")
            self.ticks_x_labels, self.ticks_y_labels = labels
        else:
            self.ticks_x_labels, self.ticks_y_labels = None, None

    def validate(self):
        if self.axis_y_max is not None and self.axis_y_min is not None:
            if self.axis_y_max <= self.axis_y_min:
                raise ValueError(f'axis_y_max ({self.axis_y_max}) must be greater than axis_y_min ({self.axis_y_min})')
        color_error = "Color for '%s' not defined in color map"
        if self.frame and 'frame' not in self.color.map:
            raise ValueError(color_error % 'frame')
        if (self.grid_x_dash is not None or self.grid_y_dash is not None) and 'grid' not in self.color.map:
            raise ValueError(color_error % 'grid')
        if (self.axis_x or self.axis_y) and 'axis' not in self.color.map:
            raise ValueError(color_error % 'axis')
        if (((self.ticks_x_labels is not None and len(self.ticks_x_labels) > 0)
            or (self.ticks_y_labels is not None and len(self.ticks_y_labels) > 0))
                and 'labels' not in self.color.map):
            raise ValueError(color_error % 'labels')


    def _draw_axes(self, fb: FrameBufferExtension):
        if self.axis_x:
            fb.line(0, fb.height - 1, fb.width - 1, fb.height - 1, self.color.map['axis'])  # X axis
        if self.axis_y:
            fb.line(0, 0, 0, fb.height - 1, self.color.map['axis'])  # Y axis

    def _draw_grid(self, fb: FrameBufferExtension, x_count: int, y_count: int):
        logger.debug(f'Drawing grid {x_count} x {y_count}')
        if self.grid_x_dash is not None:
            for v in range(0, x_count):
                x = int((v / (x_count - 1)) * (fb.width - 1))
                logger.debug(f"Drawing vertical grid #{v} line at x={x}")
                fb.seg_vline(x, 0, fb.height, self.color.map['grid'], dash=self.grid_x_dash)
        if self.grid_y_dash is not None:
            for h in range(0, y_count):
                # y = fb.height - int((h / (y_count - 1)) * fb.height)
                y = int((h / (y_count - 1)) * (fb.height - 1))
                logger.debug(f"Drawing horizontal grid #{h} line at y={y}")
                fb.seg_hline(0, y, fb.width , self.color.map['grid'], dash=self.grid_y_dash)

    def _draw_ticks(self, fb: FrameBufferExtension, x_count: int, y_count: int):
        if self.ticks_x_length:
            for i in range(x_count):
                x = int((i / (x_count - 1)) * (fb.width - 1))
                if self.ticks_x_pos == TICK_BELOW:
                    y0 = fb.height - 1
                    y1 = fb.height - 1 + self.ticks_x_length
                elif self.ticks_x_pos == TICK_ABOVE:
                    y0 = fb.height - 1 - self.ticks_x_length
                    y1 = fb.height - 1
                else:  # TICK_CENTER
                    y0 = fb.height - 1 - (self.ticks_x_length // 2)
                    y1 = fb.height - 1 + (self.ticks_x_length // 2)
                fb.line(x, y0, x, y1, self.color.map['ticks'])
        if self.ticks_y_length:
            for i in range(y_count):
                y = int((i / (y_count - 1)) * (fb.height - 1))
                if self.ticks_y_pos == TICK_LEFT:
                    x0 = 0 - self.ticks_y_length
                    x1 = 0
                elif self.ticks_y_pos == TICK_RIGHT:
                    x0 = 0
                    x1 = 0 + self.ticks_y_length
                else:  # TICK_CENTER
                    x0 = 0 - (self.ticks_y_length // 2)
                    x1 = 0 + (self.ticks_y_length // 2)
                fb.line(x0, y, x1, y, self.color.map['ticks'])

    def _draw_x_labels(self, fb: FrameBufferExtension, xs: list, x_ticks_count: int):
        logger.debug(f"Drawing X labels: {xs}, ticks per label: {self.ticks_x_per_label}, ticks count: {x_ticks_count}")
        if xs and len(xs) > 0:
            n = len(xs)
            for i in range(0, n * self.ticks_x_per_label, self.ticks_x_per_label):
                x = int((i / (x_ticks_count - 1)) * (fb.width - 1))
                text = str(xs[i // self.ticks_x_per_label])
                text_width = self.font.size(text)[0]
                text_x = x - (text_width // 2)
                text_y = fb.height + 1
                logger.debug(f'  X label #{i}: "{text}" at ({text_x},{text_y})')
                fb.textf(text, text_x, text_y, self.font)

    def _draw_y_labels(self, fb: FrameBufferExtension, ys: list, y_ticks_count: int):
        logger.debug(f"Drawing Y labels: {ys}")
        if ys and len(ys) > 0:
            n = len(ys)
            for i in range(0, n * self.ticks_y_per_label, self.ticks_y_per_label):
                y = fb.height - int((i / (y_ticks_count - 1)) * (fb.height - 1))
                text = str(ys[i // self.ticks_y_per_label])
                text_width = self.font.size(text)[0]
                text_x = 0 - text_width - 2
                text_y = y - (self.font.height // 2)
                logger.debug(f'  Y label #{i}: "{text}" at ({text_x},{text_y})')
                fb.textf(text, text_x, text_y, self.font)



    @staticmethod
    def _choose_count(a, b, autogenerate=None):
        return a if a is not None else (b if b is not None else autogenerate)

    def draw_series(self, fb: FrameBufferExtension, xs: list, ys: list):
        raise NotImplementedError

    def draw(self, fb: FrameBufferExtension, xs: list, ys: list):
        logger.debug(f'Drawing chart of type "{type}')
        self.validate()
        if self.frame:
            fb.rect(0, 0, fb.width, fb.height, self.color.map['frame'], False)

        chart = FrameBufferOffset(fb, self.margin_left, 0, fb.width - self.margin_left - 1, fb.height - self.margin_bottom - 1)

        ticks_x_count = self._choose_count(self.ticks_x_count, self.grid_x_count, len(ys) + 1)
        ticks_y_count = self._choose_count(self.ticks_y_count ,self.grid_y_count, fb.height // 10)
        self._draw_grid(chart, self._choose_count(self.grid_x_count, ticks_x_count), self._choose_count(self.grid_y_count, ticks_y_count))
        self._draw_ticks(chart, ticks_x_count, ticks_y_count)

        self._draw_axes(chart)

        def pickup_labels(xs: list, n: int) -> list:
            logger.debug(f"pickup_labels: xs={xs}, n={n}")
            if not xs or n <= 0:
                return []
            if n == 1:
                return [xs[0]]
            step = (len(xs) - 1) / (n - 1)
            return [xs[int(round(i * step))] for i in range(n)]

        x_labels = self.ticks_x_labels if self.ticks_x_labels else pickup_labels(xs, ticks_x_count // self.ticks_x_per_label)
        self._draw_x_labels(chart, x_labels, ticks_x_count)

        y_labels = self.ticks_y_labels if self.ticks_y_labels is not None else pickup_labels(
            [round(self.axis_y_min + (i / (ticks_y_count - 1)) * (self.axis_y_max - self.axis_y_min), 1) for i in range(ticks_y_count)],
            (ticks_y_count // self.ticks_y_per_label) + (1 if ticks_y_count % self.ticks_y_per_label != 0 else 0)
        )
        self._draw_y_labels(chart, y_labels, ticks_y_count)

        arena = FrameBufferOffset(chart, 1, 0, chart.width - 1, chart.height - 1)
        self.draw_series(arena, xs, ys)
        logger.debug("Chart drawing completed.")


class BarPlot(Plot):

    def validate(self):
        super().validate()
        if 'bars' not in self.color.map:
            raise ValueError("Color for 'bars' not defined in color map")

    def draw_series(self, fb: FrameBufferExtension, xs: list, ys: list):
        upper_value = self.axis_y_max if self.axis_y_max is not None else max(ys)
        n = len(ys)
        logger.debug(f"Drawing bars: n={n}, upper_value={upper_value}, fb=({fb.width}x{fb.height})")
        if n == 0:
            return
        for i in range(n):
            bar_height = int((ys[i] / upper_value) * fb.height) if upper_value > 0 else 0
            x0 = int((i / n) * fb.width)
            y0 = fb.height - bar_height
            x1 = int(((i + 1) / n) * fb.width)
            y1 = fb.height - 1
            logger.debug(f"  Bar #{i}: value={ys[i]}, height={bar_height}, coords=({x0},{y0})-({x1},{y1})")
            fb.rect(x0, y0, x1 - x0, y1 - y0 + 1, self.color.map['bars'], True)
