import logging

from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset

logger = logging.getLogger(__name__)

TICK_BELOW = 0
TICK_CENTER = 1
TICK_ABOVE = 2

TICK_LEFT = 0
TICK_RIGHT = 2

class Plot:

    def __init__(self, colormap: dict, font: FrameBufferFont):
        self.colormap = colormap
        self.font = font

        self.frame = False  # draw frame around chart

        # self.axes(left: bool | None, top: bool | None, right: bool | None, bottom: bool | None) OR:
        self.axis_bottom = True  # draw bottom axis
        self.axis_left = True  # draw left axis
        self.axis_right = False   # draw right axis
        self.axis_top = False  # draw top axis

        self.axis_y_min = 0
        self.axis_y_max = 5

        # self.margins(left: int | None, top: int | None, right: int | None, bottom: int | None) OR:
        self.margin_left = 0  # left margin for Y axis
        self.margin_bottom = 0  # bottom margin for X axis
        self.margin_right = 0 # right margin
        self.margin_top = 0  # top margin

        # self.grid_dash(vert: tuple[tuple[int, int] | None, horiz: tuple[int, int] | None]) OR:
        self.grid_dash_vert = (1, 5)  # grid's on/off segments ; None = no grid
        self.grid_dash_horiz = (1, 5)  # grid's on/off segments ; None = no grid

        # self.grid_count(vert: int | None, horiz: int | None) OR:
        self.grid_count_vert = None  # number of vertical grid lines; if None, align with ticks_x_count or auto generate
        self.grid_count_horiz = None  # number of horizontal grid lines; if None, align with ticks_y_count or auto generate

        # self.ticks_length(bottom: int | None, left: int | None, right: int | None, top: int | None) OR:
        self.ticks_length_bottom = 3  # length of bottom ticks; if None or 0, no ticks
        self.ticks_length_left = 3  # length of left ticks; if None or 0, no ticks
        self.ticks_length_top = None  # length of bottom ticks; if None or 0, no ticks
        self.ticks_length_right = None  # length of left ticks; if None or 0, no ticks

        # self.ticks_pos(bottom: int | None, left: int | None, right: int | None, top: int | None) OR:
        self.ticks_pos_bottom = TICK_CENTER  # position of bottom ticks
        self.ticks_pos_left = TICK_CENTER  # position of left ticks
        self.ticks_pos_top = TICK_CENTER  # position of top ticks
        self.ticks_pos_right = TICK_CENTER  # position of right ticks

        # self.ticks_count(bottom: int | None, left: int | None, right: int | None, top: int | None) OR:
        self.ticks_count_bottom = None  # number of X ticks; if None, align with grid_count_bottom or auto generate
        self.ticks_count_left = None  # number of Y ticks; if None, align with grid_count_left or auto generate
        self.ticks_count_top = None  # number of X ticks; if None, align with grid_count_top or auto generate
        self.ticks_count_right = None  # number of Y ticks; if None, align

        # self.signals(bottom: list | None, left: list | None, right: list | None, top: list | None) OR:
        self.signals_bottom = []  # list of tick indexes to differentiate (e.g. draw circle); bottom
        self.signals_left = []  # list of tick indexes to differentiate (e.g. draw circle); left
        self.signals_top = []  # list of tick indexes to differentiate (e.g. draw circle); top
        self.signals_right = []  # list of tick indexes to differentiate (e.g. draw circle); right

        self.signals_size = 5  # size of the signal sign

        # self.ticks_labels(bottom: bool | None, left: bool | None, right: bool | None, top: bool | None) OR:
        self.ticks_labels_bottom = True
        self.ticks_labels_left = True
        self.ticks_labels_top = False
        self.ticks_labels_right = False

        # self.ticks_labels_list(bottom: list | None, left: list | None, right: list | None, top: list | None) OR:
        self.ticks_labels_list_bottom = None # bottom ticks labels; if None, auto generate
        self.ticks_labels_list_left = None  # left ticks labels; if None, auto generate
        self.ticks_labels_list_top = None  # top ticks labels; if None, auto generate
        self.ticks_labels_list_right =None  # right ticks labels; if None, auto generate

        # self.ticks_per_label(bottom: int | None, left: int | None, right: int | None, top: int | None) OR:
        self.ticks_per_label_bottom = 1  # number of bottom ticks per label
        self.ticks_per_label_left = 1  # number of left ticks per label
        self.ticks_per_label_top = 1  # number of top ticks per label
        self.ticks_per_label_right = 1  # number of right ticks per label

        self.label_format = lambda  x: str(x)  # function to format tick labels; by default, convert to string

    def axes(self, bottom: bool = None, left: bool = None, right: bool = None, top: bool = None):
        self.axis_bottom =  self._first_not_none(bottom, self.axis_bottom)
        self.axis_left = self._first_not_none(left, self.axis_left)
        self.axis_right = self._first_not_none(right, self.axis_right)
        self.axis_top = self._first_not_none(top, self.axis_top)
        return self.axis_left, self.axis_top, self.axis_right, self.axis_bottom

    def margins(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
        self.margin_left = left
        self.margin_bottom = bottom
        self.margin_right = right
        self.margin_top = top
        return self.margin_left, self.margin_top, self.margin_right, self.margin_bottom

    def ticks_count(self, bottom: int = None, left: int = None, right: int = None, top: int = None):
        self.ticks_count_bottom = self._first_not_none(bottom, self.ticks_count_bottom)
        self.ticks_count_left = self._first_not_none(left, self.ticks_count_left)
        self.ticks_count_right = self._first_not_none(right, self.ticks_count_right)
        self.ticks_count_top = self._first_not_none(top, self.ticks_count_top)
        return self.ticks_count_left, self.ticks_count_top, self.ticks_count_right, self.ticks_count_bottom

    def signals(self, bottom: list = None, left: list = None, right: list = None, top: list = None):
        self.signals_bottom = self._first_not_none(bottom, self.signals_bottom, [])
        self.signals_left = self._first_not_none(left, self.signals_left, [])
        self.signals_right = self._first_not_none(right, self.signals_right, [])
        self.signals_top = self._first_not_none(top, self.signals_top, [])
        return self.signals_left, self.signals_top, self.signals_right, self.signals_bottom

    def ticks_length(self, bottom: int = None, left: int = None, right: int = None, top: int = None):
        self.ticks_length_bottom = bottom
        self.ticks_length_left = left
        self.ticks_length_right = right
        self.ticks_length_top = top
        return self.ticks_length_left, self.ticks_length_top, self.ticks_length_right, self.ticks_length_bottom

    def ticks_pos(self, bottom: int = TICK_CENTER, left: int = TICK_CENTER, right: int = TICK_CENTER, top: int = TICK_CENTER):
        self.ticks_pos_bottom = bottom
        self.ticks_pos_left = left
        self.ticks_pos_right = right
        self.ticks_pos_top = top
        return self.ticks_pos_left, self.ticks_pos_top, self.ticks_pos_right, self.ticks_pos_bottom

    def ticks_per_label(self, bottom: int = None, left: int = None, right: int = None, top: int = None):
        self.ticks_per_label_bottom = self._first_not_none(bottom, self.ticks_per_label_bottom)
        self.ticks_per_label_left = self._first_not_none(left, self.ticks_per_label_left)
        self.ticks_per_label_right = self._first_not_none(right, self.ticks_per_label_right)
        self.ticks_per_label_top = self._first_not_none(top, self.ticks_per_label_top)
        return self.ticks_per_label_left, self.ticks_per_label_top, self.ticks_per_label_right, self.ticks_per_label_bottom

    def ticks_labels(self, bottom: bool = None, left: bool = None, right: bool = None, top: bool = None):
        self.ticks_labels_bottom = self._first_not_none(bottom, self.ticks_labels_bottom)
        self.ticks_labels_left = self._first_not_none(left, self.ticks_labels_left)
        self.ticks_labels_right = self._first_not_none(right, self.ticks_labels_right)
        self.ticks_labels_top = self._first_not_none(top, self.ticks_labels_top)

    def ticks_labels_list(self, bottom: list = False, left: list = False, right: list = False, top: list = False):
        self.ticks_labels_list_bottom = self._first_not_false(bottom, self.ticks_labels_list_bottom)
        self.ticks_labels_list_left = self._first_not_false(left, self.ticks_labels_list_left)
        self.ticks_labels_list_right = self._first_not_false(right, self.ticks_labels_list_right)
        self.ticks_labels_list_top = self._first_not_false(top, self.ticks_labels_list_top)
        return self.ticks_labels_list_left, self.ticks_labels_list_top, self.ticks_labels_list_right, self.ticks_labels_list_bottom

    def grid_dash(self, vert: tuple = False, horiz: tuple = False):
        if vert is not None and vert is not False  and len(vert) != 2:
            raise ValueError("vert dash must be a tuple like (on, off) or None")
        if horiz is not None and horiz is not False and len(horiz) != 2:
            raise ValueError("horiz dash must be a tuple like (on, off) or None")
        self.grid_dash_vert = self._first_not_false(vert, self.grid_dash_vert)
        self.grid_dash_horiz = self._first_not_false(horiz, self.grid_dash_horiz)
        return self.grid_dash_vert, self.grid_dash_horiz

    def grid_count(self, vert: int = None, horiz: int = None):
        self.grid_count_vert = self._first_not_none(vert, self.grid_count_vert)
        self.grid_count_horiz = self._first_not_none(horiz, self.grid_count_horiz)
        return self.grid_count_vert, self.grid_count_horiz

    @staticmethod
    def _first_not_false(a, b):
        return a if a is not False else b

    @staticmethod
    def _first_not_none(a, b, autogenerate=None):
        return a if a is not None else (b if b is not None else autogenerate)

    def validate(self):
        if self.axis_y_max is not None and self.axis_y_min is not None:
            if self.axis_y_max <= self.axis_y_min:
                raise ValueError(f'axis_y_max ({self.axis_y_max}) must be greater than axis_y_min ({self.axis_y_min})')
        color_error = "Color for '%s' not defined in color map"
        if self.frame and 'frame' not in self.colormap:
            raise ValueError(color_error % 'frame')
        if (self.grid_dash_vert is not None or self.grid_dash_horiz is not None) and 'grid' not in self.colormap:
            raise ValueError(color_error % 'grid')
        if ((self.axis_bottom or self.axis_left or self.axis_top or self.axis_right)
                and 'axis' not in self.colormap):
            raise ValueError(color_error % 'axis')
        if (((self.ticks_labels_list_bottom is not None and len(self.ticks_labels_list_bottom) > 0)
            or (self.ticks_labels_list_left is not None and len(self.ticks_labels_list_left) > 0))
                and 'labels' not in self.colormap):
            raise ValueError(color_error % 'labels')


    def _draw_axes(self, fb: FrameBufferExtension):
        if self.axis_bottom:
            fb.line(0, fb.height - 1, fb.width - 1, fb.height - 1, self.colormap['axis'])  # X axis
        if self.axis_left:
            fb.line(0, 0, 0, fb.height - 1, self.colormap['axis'])  # Y axis
        if self.axis_top:
            fb.line(0, 0, fb.width - 1, 0, self.colormap['axis'])  # Top axis
        if self.axis_right:
            fb.line(fb.width - 1, 0, fb.width - 1, fb.height - 1, self.colormap['axis'])  # Right axis

    def _draw_grid(self, fb: FrameBufferExtension, x_count: int, y_count: int):
        logger.debug(f'Drawing grid {x_count} x {y_count}')
        if self.grid_dash_vert is not None:
            for v in range(0, x_count):
                x = int((v / (x_count - 1)) * (fb.width - 1))
                logger.debug(f"Drawing vertical grid #{v} line at x={x}")
                fb.seg_vline(x, 0, fb.height, self.colormap['grid'], dash=self.grid_dash_vert)
        if self.grid_dash_horiz is not None:
            for h in range(0, y_count):
                # y = fb.height - int((h / (y_count - 1)) * fb.height)
                y = int((h / (y_count - 1)) * (fb.height - 1))
                logger.debug(f"Drawing horizontal grid #{h} line at y={y}")
                fb.seg_hline(0, y, fb.width, self.colormap['grid'], dash=self.grid_dash_horiz)

    def _draw_signal(self, fb: FrameBufferExtension, x, y, size: int, orientation: str):
        # x, y represents center of the signal sign
        # draw triangle around the point:
        logger.debug("Drawing signal at ({}, {}) with size {} and orientation {}".format(x, y, size, orientation))
        color = self._first_not_none(self.colormap.get('signal_ticks'), self.colormap['ticks'])
        if orientation == 'top':
            fb.triangle(x - size, y - size, x + size, y - size, x, y + size, color, True)
        elif orientation == 'bottom':
            fb.triangle(x - size, y + size, x + size, y + size, x, y - size, color, True)
        elif orientation == 'left':
            fb.triangle(x - size, y - size, x - size, y + size, x + size, y, color, True)
        elif orientation == 'right':
            fb.triangle(x + size, y - size, x + size, y + size, x - size, y, color, True)
        else:
            raise ValueError("Orientation must be 'top', 'bottom', 'left', or 'right'")

    def _draw_signals(self, fb: FrameBufferExtension, position: str, count: int, signals: list):
        for i in range(count):
            if signals and i in signals:
                coord  = int((i / (count - 1)) * (fb.width - 1)) if position in ['bottom', 'top'] else int((i / (count - 1)) * (fb.height - 1))
                if position == 'bottom':
                    self._draw_signal(fb, coord, fb.height - 1 - self.signals_size, self.signals_size, position)
                elif position == 'top':
                    self._draw_signal(fb, coord, self.signals_size, self.signals_size, position)
                elif position == 'left':
                    self._draw_signal(fb, self.signals_size, coord, self.signals_size, position)
                elif position == 'right':
                    self._draw_signal(fb, fb.width - 1 - self.signals_size, coord, self.signals_size, position)
                else:
                    raise ValueError("Position must be 'bottom', 'top', 'left', or 'right'")

    def _draw_ticks(self, fb: FrameBufferExtension, position, count: int, length: int, pos_type: int):
        for i in range(count):
            coord  = int((i / (count - 1)) * (fb.width - 1)) if position in ['bottom', 'top'] else int((i / (count - 1)) * (fb.height - 1))
            if position == 'bottom':
                if pos_type == TICK_BELOW:
                    y0 = fb.height - 1
                    y1 = fb.height - 1 + length
                elif pos_type == TICK_ABOVE:
                    y0 = fb.height - 1 - length
                    y1 = fb.height - 1
                else:  # TICK_CENTER
                    y0 = fb.height - 1 - (length // 2)
                    y1 = fb.height - 1 + (length // 2)
                fb.line(coord, y0, coord, y1, self.colormap['ticks'])
            elif position == 'left':
                if pos_type == TICK_LEFT:
                    x0 = 0 - length
                    x1 = 0
                elif pos_type == TICK_RIGHT:
                    x0 = 0
                    x1 = 0 + length
                else:  # TICK_CENTER
                    x0 = 0 - (length // 2)
                    x1 = 0 + (length // 2)
                fb.line(x0, coord, x1, coord, self.colormap['ticks'])
            elif position == 'right':
                if pos_type == TICK_LEFT:
                    x0 = fb.width - 1
                    x1 = fb.width - 1 + length
                elif pos_type == TICK_RIGHT:
                    x0 = fb.width - 1 - length
                    x1 = fb.width - 1
                else:  # TICK_CENTER
                    x0 = fb.width - 1 - (length // 2)
                    x1 = fb.width - 1 + (length // 2)
                fb.line(x0, coord, x1, coord, self.colormap['ticks'])
            elif position == 'top':
                if pos_type == TICK_BELOW:
                    y0 = 0 - length
                    y1 = 0
                elif pos_type == TICK_ABOVE:
                    y0 = 0
                    y1 = 0 + length
                else:  # TICK_CENTER
                    y0 = 0 - (length // 2)
                    y1 = 0 + (length // 2)
                fb.line(coord, y0, coord, y1, self.colormap['ticks'])

    def _draw_horiz_labels(self, fb: FrameBufferExtension, position: str, xs: list, x_ticks_count: int):
        if position not in ['bottom', 'top']:
            raise ValueError("Position must be 'bottom' or 'top'")
        ticks_per_label = self.ticks_per_label_bottom if position == 'bottom' else self.ticks_per_label_top
        logger.debug(f"Drawing HORIZ labels at {position}: {xs}, ticks per label: {ticks_per_label}, ticks count: {x_ticks_count}")
        if xs and len(xs) > 0:
            n = len(xs)
            for i in range(0, n * ticks_per_label, ticks_per_label):
                x = int((i / (x_ticks_count - 1)) * (fb.width - 1))
                text = self.label_format(xs[i // ticks_per_label])
                text_width = self.font.size(text)[0]
                text_x = x - (text_width // 2)
                text_y = fb.height + 1 if position == 'bottom' else 0 - self.font.height - 1
                logger.debug(f'  X label #{i}: "{text}" at ({text_x},{text_y})')
                fb.textf(text, text_x, text_y, self.font)

    def _draw_vert_labels(self, fb: FrameBufferExtension, position: str, ys: list, y_ticks_count: int):
        if position not in ['left', 'right']:
            raise ValueError("Position must be 'left' or 'right'")
        ticks_per_label = self.ticks_per_label_left if position == 'left' else self.ticks_per_label_right
        logger.debug(f"Drawing VERT labels at {position}: {ys}, ticks per label: {ticks_per_label}, ticks count: {y_ticks_count}")
        if ys and len(ys) > 0:
            n = len(ys)
            for i in range(0, n * ticks_per_label, ticks_per_label):
                y = fb.height - int((i / (y_ticks_count - 1)) * (fb.height - 1))
                text = self.label_format(ys[i // ticks_per_label])
                text_width = self.font.size(text)[0]
                text_x = 0 - text_width - 2 if position == 'left' else fb.width + 2
                text_y = y - (self.font.height // 2)
                logger.debug(f'  Y label #{i}: "{text}" at ({text_x},{text_y})')
                fb.textf(text, text_x, text_y, self.font)

    def draw_series(self, fb: FrameBufferExtension, xs: list, ys: list):
        raise NotImplementedError

    def draw(self, fb: FrameBufferExtension, xs: list, ys: list):
        self.validate()
        if self.frame:
            fb.rect(0, 0, fb.width, fb.height, self.colormap['frame'], False)

        chart = FrameBufferOffset(fb,
                                  self.margin_left,
                                  self.margin_top,
                                  fb.width - self.margin_left - self.margin_right - 1,
                                  fb.height - self.margin_top - self.margin_bottom - 1)

        ticks_y_count_left = self._first_not_none(self.ticks_count_left, self.grid_count_horiz, fb.height // 10)
        ticks_x_count_top = self._first_not_none(self.ticks_count_top, self.grid_count_vert, len(ys) + 1)
        ticks_y_count_right = self._first_not_none(self.ticks_count_right, self.grid_count_horiz, fb.height // 10)
        ticks_x_count_bottom = self._first_not_none(self.ticks_count_bottom, self.grid_count_vert, len(ys) + 1)

        self._draw_grid(chart, self._first_not_none(self.grid_count_vert, ticks_x_count_bottom), self._first_not_none(self.grid_count_horiz, ticks_y_count_left))

        if self.ticks_length_left:
            self._draw_ticks(chart, 'left', ticks_y_count_left, self.ticks_length_left, self.ticks_pos_left)
        if self.ticks_length_top:
            self._draw_ticks(chart, 'top', ticks_x_count_top, self.ticks_length_top, self.ticks_pos_top)
        if self.ticks_length_right:
            self._draw_ticks(chart, 'right', ticks_y_count_right, self.ticks_length_right, self.ticks_pos_right)
        if self.ticks_length_bottom:
            self._draw_ticks(chart, 'bottom', ticks_x_count_bottom, self.ticks_length_bottom, self.ticks_pos_bottom)

        logger.debug(f"SIGNAL TICKS: {self.signals()}")
        if self.signals_left:
            self._draw_signals(chart, 'left', ticks_y_count_left, self.signals_left)
        if self.signals_top:
            self._draw_signals(chart, 'top', ticks_x_count_top, self.signals_top)
        if self.signals_right:
            self._draw_signals(chart, 'right', ticks_y_count_right, self.signals_right)
        if self.signals_bottom:
            self._draw_signals(chart, 'bottom', ticks_x_count_bottom, self.signals_bottom)

        self._draw_axes(chart)

        def pickup_labels(xs: list, n: int) -> list:
            logger.debug(f"pickup_labels: xs={xs}, n={n}")
            if not xs or n <= 0:
                return []
            if n == 1:
                return [xs[0]]
            step = (len(xs) - 1) / (n - 1)
            return [xs[int(round(i * step))] for i in range(n)]

        # Horizontal labels:
        if self.ticks_labels_bottom:
            picked_x_labels = pickup_labels(xs, ticks_x_count_bottom // self.ticks_per_label_bottom)
            x_labels = self.ticks_labels_list_bottom if self.ticks_labels_list_bottom else picked_x_labels
            self._draw_horiz_labels(chart, 'bottom', x_labels, ticks_x_count_bottom)
        if self.ticks_labels_top:
            picked_x_labels = pickup_labels(xs, ticks_x_count_top // self.ticks_per_label_top)
            x_labels = self.ticks_labels_list_top if self.ticks_labels_list_top else picked_x_labels
            self._draw_horiz_labels(chart, 'top', x_labels, ticks_x_count_top)

        # Vertical labels:
        if self.ticks_labels_left:
            picked_y_labels = pickup_labels(
                [round(self.axis_y_min + (i / (ticks_y_count_left - 1)) * (self.axis_y_max - self.axis_y_min), 1) for i in range(ticks_y_count_left)],
                (ticks_y_count_left // self.ticks_per_label_left) + (1 if ticks_y_count_left % self.ticks_per_label_left != 0 else 0)
            )
            y_labels = self.ticks_labels_list_left if self.ticks_labels_list_left is not None else picked_y_labels
            self._draw_vert_labels(chart, 'left', y_labels, ticks_y_count_left)
        if self.ticks_labels_right:
            picked_y_labels = pickup_labels(
                [round(self.axis_y_min + (i / (ticks_y_count_right - 1)) * (self.axis_y_max - self.axis_y_min), 1) for i in range(ticks_y_count_right)],
                (ticks_y_count_right // self.ticks_per_label_left) + (1 if ticks_y_count_right % self.ticks_per_label_left != 0 else 0)
            )
            y_labels = self.ticks_labels_list_right if self.ticks_labels_list_right is not None else picked_y_labels
            self._draw_vert_labels(chart, 'right', y_labels, ticks_y_count_right)

        arena = FrameBufferOffset(chart, 1, 1, chart.width - 2, chart.height - 2)
        self.draw_series(arena, ys)
        logger.debug("Chart drawing completed.")


class BarPlot(Plot):

    def validate(self):
        super().validate()
        if 'bars' not in self.colormap:
            raise ValueError("Color for 'bars' not defined in color map")

    def draw_series(self, fb: FrameBufferExtension, ys: list):
        upper_value = self.axis_y_max if self.axis_y_max is not None else max(ys)
        n = len(ys)
        logger.debug(f"BAR PLOT: n={n}, upper_value={upper_value}, fb=({fb.width}x{fb.height})")
        if n == 0:
            return
        for i in range(n):
            if ys[i] is not None:
                bar_height = int((ys[i] / upper_value) * fb.height) if upper_value > 0 else 0
                x0 = int((i / n) * fb.width)
                y0 = fb.height - bar_height
                x1 = int(((i + 1) / n) * fb.width)
                y1 = fb.height - 1
                logger.debug(f"  Bar #{i}: value={ys[i]}, height={bar_height}, coords=({x0},{y0})-({x1},{y1})")
                fb.rect(x0, y0, x1 - x0, y1 - y0 + 1, self.colormap['bars'], True)
            else:
                logger.debug(f"  Bar #{i}: None")



class LinePlot(Plot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dot_size = 0

    def validate(self):
        super().validate()
        if 'line' not in self.colormap:
            raise ValueError("Color for 'line' not defined in color map")
        if self.dot_size > 0 and 'dot' not in self.colormap:
            raise ValueError("Color for 'dot' not defined in color map")

    def draw_series(self, fb: FrameBufferExtension, ys: list):
        upper_value = self.axis_y_max if self.axis_y_max is not None else max(ys)
        lower_value = self.axis_y_min if self.axis_y_min is not None else min(ys)
        value_range = upper_value - lower_value or 1  # avoid div by zero

        # For line plot, we have to cut the frame buffer on the right by the size of one tick.
        # This way, the plot points will match the ticks below.
        arena = FrameBufferOffset(fb, 0, 0, fb.width - (fb.width // (len(ys) if len(ys) > 1 else 1)), fb.height)

        n = len(ys)
        logger.debug(f"LINE PLOT: n={n}, upper_value={upper_value}, fb=({arena.width}x{arena.height})")
        if n == 0:
            return
        x, y = None, None

        for i in range(n):
            y_value = ys[i]
            if y_value is None:
                x, y = None, None
                continue
            y_norm = (y_value - lower_value) / value_range
            y_pos = arena.height - 1 - int(y_norm * (arena.height - 1))
            x_pos = int((i / (n - 1)) * (arena.width - 1)) if n > 1 else 0
            logger.debug(f"  Point #{i}: value={y_value}, pos=({x_pos},{y_pos})")
            if x is not None and y is not None:
                arena.line(x, y, x_pos, y_pos, self.colormap['line'])
                arena.ellipse(x, y, self.dot_size, self.dot_size, self.colormap['dot'], True)
            if self.dot_size > 0:
                arena.ellipse(x_pos, y_pos, self.dot_size, self.dot_size, self.colormap['dot'], True)
            x, y = x_pos, y_pos
