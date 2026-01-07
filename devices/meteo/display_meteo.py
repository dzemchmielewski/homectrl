import framebuf
import json
import time

if __name__ == "__main__":
    import sys
    sys.path.append('../../micropython')
    sys.path.append('../../devel')

from meteoparts.astropart import AstroPart
from meteoparts.precipitationpart import PrecipitationPart
from plot import *
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset
from colors import Colors


class MeteoDisplay:

    def __init__(self, width: int, height: int, fb_mode: framebuf.MONO_HLSB):
        self.fb = FrameBufferExtension(width, height, fb_mode)

        self.colors = Colors([0, 1, 2, 3])  # 4-level scale
        self.colors.map = self.colors.map | {
            'axis': self.colors.BLACK,
            'grid': self.colors.LIGHT,
            'bars': self.colors.DARK,
            'frame': self.colors.LIGHT,
            'labels': self.colors.BLACK,
            'ticks': self.colors.BLACK,
        }

        self.background = self.colors.WHITE
        self.foreground = self.colors.BLACK

        self.font_palette = FrameBufferExtension(4, 1, framebuf.GS2_HMSB)
        self.font_palette.pixel(0, 0, 3)  # background color
        self.font_palette.pixel(1, 0, 0)  # dash color
        self.font_palette.pixel(2, 0, 1)  # unused
        self.font_palette.pixel(3, 0, 2)  # unused

        self.fonts_middle = FrameBufferFont("fonts/LiberationSerif-Bold.52.mfnt", palette=self.font_palette)
        self.font_topbottom = FrameBufferFont("fonts/LiberationSans-Bold.18.mfnt", palette=self.font_palette)
        self.font_hour = FrameBufferFont("fonts/LiberationMono-Italic.12.mfnt", palette=self.font_palette)

        self.font_small = FrameBufferFont("fonts/LiberationSans-Bold.12.mfnt", palette=self.font_palette)


    def clear(self):
        self.fb.fill(self.background)

    def _temperature(self, temperature: float) -> (int, int):
        font = self.fonts_middle

        # Render temperature
        x_spacing = 6
        temperature_str = f"{temperature:.1f}"
        size_x, size_y = font.size(f"{temperature_str}.C", x_spacing=x_spacing)
        size_x, size_y = size_x + 7, size_y  # extra for degree symbol
        x, y = self.fb.width // 2 - (size_x // 2), self.fb.height // 2 - (size_y // 2)

        #key=self.background
        x, y = self.fb.textf(f"{temperature_str}", x, y, font, x_spacing=x_spacing)

        # Degree symbol
        x, y = x + font.get_char('.')[2], y - font.height + round(font.height * (2/10))
        self.fb.ellipse(x, y, 6, 6, self.foreground, True)
        self.fb.ellipse(x, y, 3, 3, self.background, True)

        # "C" symbol
        x, y = x + 7, y - 10
        x, y = self.fb.textf("C", x, y, font, key=self.background)
        return x, y

    def update(self, data: dict):
        self.fb.fill(self.background)
        # self._temperature(data['meteo']['temperature'])

        self.fb.textf(f"{data['meteo']['pressure']['real']:.1f} hPa", 10, 8, self.font_topbottom, key=self.background)

        time_str = f"{data['meteo']['date'][11:13]}:{data['meteo']['date'][14:16]}"
        time_str_len, _ = self.font_hour.size(time_str)
        week_length, _ = self.font_topbottom.size(data['astro']['datetime']['weekday'])

        x, y = self.fb.textf(time_str,
                             self.fb.width - (10 + time_str_len + week_length), 8 + 4,
                             self.font_hour, key=self.background)
        x, y = self.fb.textf(f"{data['astro']['datetime']['weekday']}",
                             x + 4, 8,
                             self.font_topbottom, key=self.background)


        # precipitation = f"{meteo_data['precipitation']:.1f}mm ({meteo_data['humidity']:.0f}%)"
        # self.fb.textf(precipitation, 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)
        #
        # wind = f"{meteo_data['wind']['speed']:.1f}m/s {meteo_data['wind']['direction_desc']}"
        # x,y = self.font_topbottom.size(wind)
        # self.fb.textf(wind, self.fb.width - x - 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)

        astro_widgets = AstroPart(data['astro'], self.colors)
        #astro_widgets_width = self.fb.width - 10
        astro_widgets_width = 780

        # Sun & Moon calendar widget:
        x, y = 10, 397
        _, y = astro_widgets.weekday_axis(
            FrameBufferOffset(self.fb, x, y, astro_widgets_width, 20),
            FrameBufferFont("fonts/LiberationSans-Bold.16.mfnt", palette=self.font_palette))

        x, y = x, y + 5
        astro_widgets.sun_axis(
            FrameBufferOffset(self.fb, x, y, astro_widgets_width, 20),
            self.font_small)

        x, y = x, y + 19
        _, y = astro_widgets.moon_axis(
            FrameBufferOffset(self.fb, x, y, astro_widgets_width, 20),
            self.font_small)

        x, y = x, y + 2
        astro_widgets.moon_phase_axis(
            FrameBufferOffset(self.fb, x, y, astro_widgets_width, 20),
            FrameBufferFont("fonts/LiberationSans-Bold.14.mfnt", palette=self.font_palette),
            x_padding=2)


        # Precipitation part:
        x, y = x, 330
        width, height = 785, 60,
        PrecipitationPart(data['astro'], self.colors).draw(
            FrameBufferOffset(self.fb, x, y, width, height),
            self.font_small,
            data['precipitation']['time'],
            data['precipitation']['values'],
            data['meteofcst']['time'],
            data['meteofcst']['precipitation']['average'])

        # Nothing so far:
        logger.debug(" ============================== ")
        chart_widget = LinePlot(self.colors.map | {'line': self.colors.BLACK, 'dot': self.colors.DARK}, self.font_small)
        chart_widget.frame = True
        chart_widget.axes(left=True, top=True, right=True, bottom=True)
        chart_widget.axis_y_max = 15
        chart_widget.ticks_count(bottom=13, left=7, top=13, right=7)
        chart_widget.grid_count(horiz=4, vert=7)
        chart_widget.grid_dash(vert=(3, 2), horiz=(3, 2))
        chart_widget.margins(left=30, bottom=20, right=7, top=7)
        chart_widget.ticks_per_label(bottom=2, left=2, top=2, right=2)
        chart_widget.ticks_length(bottom=5, left=5, top=5, right=5)
        chart_widget.dot_size = 3
        import random
        multi = 1
        chart_widget.draw(FrameBufferOffset(self.fb, 10, 50, 301, 150),
            ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"] * multi,
            [random.randint(0,150)/10 for _ in range(6)] * multi
            # [0] * 6 * multi
        )

        logger.debug(" ============================== ")
        self.fb.rectround(350, 50, 200, 100, self.colors.LIGHT, 10,True)


def test_screen(self):
        self.fb.fill(self.background)
        for i in range(0, self.fb.width, 50):
            self.fb.vline(i, 0, self.fb.height, self.foreground)
        for i in range(0, self.fb.height, 50):
            self.fb.hline(0, i, self.fb.width, self.foreground)
        self.fb.line(0, 0, self.fb.width - 1, self.fb.height - 1, self.foreground)
        self.fb.line(0, self.fb.height - 1, self.fb.width - 1, 0, self.foreground)
        self.fb.text("5. ALA ma Kota - ALICE has a Pussy", 55, 55, self.foreground)
        frame = FrameBufferOffset(self.fb, 250, 150, 200, 50)
        for i in range(0, 4):
            frame.rect(i * 50, 0, 50, 50, i, True)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("meteo_display")
    logging.getLogger('plot').setLevel(logging.INFO)
    logging.getLogger('toolbox.framebufext').setLevel(logging.INFO)

    data = {
        'astro': json.loads(open("astro.json").read()),
        'meteo': json.loads(open("meteo.json").read()),
        'precipitation': json.loads(open("precipitation.json").read()),
        'meteofcst': json.loads(open("meteofcst.json").read())['meteofcst']
    }

    # Mangling data:
    from_day_offset = -1
    to_day_offset = 4

    # Astro:
    # Pick only 5 days of astro data:
    data['astro']['astro'] = [astro_data for astro_data in data['astro']['astro'] if astro_data['day']['day_offset'] in range(from_day_offset, to_day_offset)]
    logger.debug(f"Astro data: {data['astro']}")

    # # Precipitation:
    # #TODO: remove random test data
    # import random
    # data['precipitation']['values'] = [random.randint(0, 48) / 10 for _ in range(0, len(data['precipitation']['values']))]
    # data['meteofcst']['precipitation']['average'] = [random.randint(0, 48) / 10 for _ in range(0, len(data['meteofcst']['precipitation']['average']))]


    meteo = MeteoDisplay(800, 480, framebuf.GS2_HMSB)
    meteo.update(data)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("TEST SCREEN OUTPUT TO /tmp/output.pgm")

    from pgmexporter import PGMExporter
    # meteo.test_screen()

    # mono_palette = FrameBufferExtension(8, 1, framebuf.MONO_HLSB)
    # mono_palette.pixel(0, 0, 0)
    # mono_palette.pixel(1, 0, 0)
    # mono_palette.pixel(2, 0, 0)
    # mono_palette.pixel(3, 0, 1)

    PGMExporter("/tmp/output.pgm").export_fbext(meteo.fb)
    # PGMExporter("/tmp/output.pgm").export_fbext(meteo.fb.convert(framebuf.MONO_HLSB, mono_palette))

    # sometest = MeteoDisplay(800, 480, framebuf.MONO_HLSB)
    # sometest.test_screen()
    # PGMExporter("/tmp/sometest.pgm").export_fbext(sometest.fb)