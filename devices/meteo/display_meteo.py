import framebuf
import json

if __name__ == "__main__":
    import sys
    sys.path.append('../../micropython')
    sys.path.append('../../devel')

from meteoparts.astropart import AstroPart
from meteoparts.temperaturestrip import TemperatureStrip
from meteoparts.precipitationstrip import PrecipitationStrip
from plot import *
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset
from colors import Colors

class FontManager:

    FAMILY_LIBERATION = "Liberation"
    CLASSIFICATION_SANS = "Sans"
    CLASSIFICATION_SERIF = "Serif"
    CLASSIFICATION_MONO = "Mono"
    WEIGHT_REGULAR = "Regular"
    WEIGHT_BOLD = "Bold"

    def __init__(self, default_palette: FrameBufferExtension = None):
        self.default_palette = default_palette
        self.fonts = {}

    def _get(self, family: str = FAMILY_LIBERATION, classification: str = CLASSIFICATION_SANS, weight: str = WEIGHT_BOLD, size: int = 14, palette: FrameBufferExtension = None):
        font_file = f"fonts/{family}{classification}-{weight}.{size}.mfnt"
        if not self.fonts.get(font_file):
            self.fonts[font_file] = FrameBufferFont(font_file, palette=palette if palette else self.default_palette)
        return self.fonts[font_file]

    def get_sans_bold(self, size: int, palette: FrameBufferExtension = None):
        return self._get(classification=self.CLASSIFICATION_SANS, weight=self.WEIGHT_BOLD, size=size, palette=palette)
    def get_sans_regular(self, size: int, palette: FrameBufferExtension = None):
        return self._get(classification=self.CLASSIFICATION_SANS, weight=self.WEIGHT_REGULAR, size=size, palette=palette)
    def get_serif_bold(self, size: int, palette: FrameBufferExtension = None):
        return self._get(classification=self.CLASSIFICATION_SERIF, weight=self.WEIGHT_BOLD, size=size, palette=palette)
    def get_serif_regular(self, size: int, palette: FrameBufferExtension = None):
        return self._get(classification=self.CLASSIFICATION_SERIF, weight=self.WEIGHT_REGULAR, size=size, palette=palette)

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
            'line': self.colors.BLACK,
            'dot': self.colors.BLACK,
        }

        self.background = self.colors.WHITE
        self.foreground = self.colors.BLACK

        self.palette_white = self.palette([3, 0, 1, 2])
        self.palette_light = self.palette([2, 0, 1, 3])
        self.palette_dark = self.palette([1, 0, 2, 3])
        self.palette_black = self.palette([0, 3, 0, 3])

        self.FM = FontManager(self.palette_white)

        # self.font_battery = FrameBufferFont("fonts/LiberationSans-Bold.14.mfnt", palette=self.palette_light)
        # self.font_serif_bold_52 = FrameBufferFont("fonts/LiberationSerif-Bold.52.mfnt", palette=self.palette_white)
        # self.font_sans_bold_26 = FrameBufferFont("fonts/LiberationSans-Bold.26.mfnt", palette=self.palette_white)

        self.fonts_middle = FrameBufferFont("fonts/LiberationSerif-Bold.52.mfnt", palette=self.palette_white)
        self.font_topbottom = FrameBufferFont("fonts/LiberationSans-Bold.18.mfnt", palette=self.palette_white)
        self.font_hour = FrameBufferFont("fonts/LiberationMono-Italic.12.mfnt", palette=self.palette_white)
        self.font_small = FrameBufferFont("fonts/LiberationSans-Bold.12.mfnt", palette=self.palette_white)

    def text_center(self, text: str, font: FrameBufferFont, y: int, x_spacing=0) -> (int, int):
        size_x, size_y = font.size(text, x_spacing=x_spacing)
        print(MeteoDisplay.FM)
        x = self.fb.width // 2 - (size_x // 2)
        return self.fb.textf(text, x, y, font, x_spacing=x_spacing)

    def palette(self, colors: list):
        # index 0 - background, index 1 - foreground, others - shades
        return FrameBufferExtension.palette(colors, self.fb.mode)

    @staticmethod
    def frame(fb: FrameBufferExtension, border: int, background: int):
        thickness, radius = 5, [12, 9]
        fb.rectround(0, 0, fb.width, fb.height, border, radius[0], True)
        fb.rectround(thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness, background, radius[1], True)
        return FrameBufferOffset(fb, thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness)

    def battery(self, fb, x, y, level_percent: int):
        w, h = 65, 22
        fb = FrameBufferOffset(fb, x, y, w, h)
        fb.rectround(0, 0, w, h, self.colors.LIGHT, 4, True)
        if level_percent <= 25:
            image = 'images/battery-quarter.fb'
        elif level_percent <= 50:
            image = 'images/battery-half.fb'
        elif level_percent <= 75:
            image = 'images/battery-three-quarters.fb'
        else:
            image = 'images/battery-full.fb'
        fb.blit(FrameBufferExtension.fromfile(image), 5, 3, self.colors.WHITE)
        FrameBufferOffset(fb, 25, 0, w - 25, h).textfalign(str(level_percent) + "%", self.FM.get_sans_bold(14), top_margin=2, palette=self.palette_light)
        return x + w, y + h

    def _meteo_item(self, fb, x, y, image_file: str, text: str, font: FrameBufferFont, width: int, top_margin: int = 11):
        image = FrameBufferExtension.fromfile(image_file)
        w, h = width, image.height + 2*10 + 2*5
        window = FrameBufferOffset(fb, x, y, w, h)
        window = self.frame(window, self.colors.DARK, self.colors.WHITE)
        window.blit(image, 5, 10, self.colors.WHITE)
        textframe = FrameBufferOffset(window,  image.width + 2*5, 0, window.width - (image.width + 2*5), window.height)
        textframe.textfalign(text, font, top_margin=top_margin)
        return x + w, y + h

    def temperature(self, fb, x, y, temperature: float):
        return self._meteo_item(fb, x, y, "images/temperature.fb", str(temperature) + "°C", self.FM.get_serif_bold(52), 285)

    def humidity(self, fb, x, y, humidity: int):
        return self._meteo_item(fb, x, y, "images/humidity.fb", str(humidity) + "%", self.FM.get_sans_bold(26), 140)

    def pressure(self, fb, x, y, pressure: float):
        x, y = self._meteo_item(fb, x, y, "images/pressure.fb", str(pressure), self.FM.get_sans_bold(26), 140, top_margin=0)
        fb.textf("hPa", x - 40, y - 20, self.FM.get_sans_bold(14))
        return x, y

    def wind(self, fb, x, y, speed: float):
        x, y = self._meteo_item(fb, x, y, "images/wind.fb", f"{speed}", self.FM.get_sans_bold(26), 140, top_margin=0)
        fb.textf("m/s", x - 35, y - 20, self.FM.get_sans_bold(14))
        return x, y

    def direction(self, fb, x, y, direction: str):
        return self._meteo_item(fb, x, y, "images/compass.fb", direction, self.FM.get_sans_bold(26), 140)

    def update(self, data: dict):
        self.fb.fill(self.background)
        x, y = self.battery(self.fb, 2, 2, 77)

        w = 305
        x, y = self.fb.width - 5 - w, 5
        window = self.fb.rectround(x, y, w, 248, self.colors.BLACK, 10, True)
        x, y = 10, 10
        x, y = self.temperature(window, x, y, -25.7)
        x, y =  10, y + 5
        x, _ = self.humidity(window, x, y, 95)
        x += 5
        x, y = self.pressure(window, x, y, 1011.2)
        x, y = 10, y + 5
        x, _ = self.wind(window, x, y, 15.4)
        x += 5
        x, y = self.direction(window, x, y, "SW")

        # thickness, radius = 5, [12, 9]
        # fb.rectround(0, 0, fb.width, fb.height, border, radius[0], True)
        # fb.rectround(thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness, background, radius[1], True)
        # return FrameBufferOffset(fb, thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness)



        # self._temperature(data['meteo']['temperature'])

        # self.fb.textf(f"{data['meteo']['pressure']['real']:.1f} hPa", 10, 8, self.font_topbottom, key=self.background)
        #
        # time_str = f"{data['meteo']['date'][11:13]}:{data['meteo']['date'][14:16]}"
        # time_str_len, _ = self.font_hour.size(time_str)
        # week_length, _ = self.font_topbottom.size(data['astro']['datetime']['weekday'])
        #
        # x, y = self.fb.textf(time_str,
        #                      self.fb.width - (10 + time_str_len + week_length), 8 + 4,
        #                      self.font_hour, key=self.background)
        # x, y = self.fb.textf(f"{data['astro']['datetime']['weekday']}",
        #                      x + 4, 8,
        #                      self.font_topbottom, key=self.background)


        # precipitation = f"{meteo_data['precipitation']:.1f}mm ({meteo_data['humidity']:.0f}%)"
        # self.fb.textf(precipitation, 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)
        #
        # wind = f"{meteo_data['wind']['speed']:.1f}m/s {meteo_data['wind']['direction_desc']}"
        # x,y = self.font_topbottom.size(wind)
        # self.fb.textf(wind, self.fb.width - x - 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)

        astro_widgets = AstroPart(data['astro'], self.colors)
        width, height = 760, 60

        # Sun & Moon calendar widget:
        x, y = 10, 397
        _, y = astro_widgets.weekday_axis(
            FrameBufferOffset(self.fb, x, y, width, 20),
            FrameBufferFont("fonts/LiberationSans-Bold.16.mfnt", palette=self.palette_white))

        x, y = x, y + 5
        astro_widgets.sun_axis(
            FrameBufferOffset(self.fb, x, y, width, 20),
            self.font_small)

        x, y = x, y + 19
        _, y = astro_widgets.moon_axis(
            FrameBufferOffset(self.fb, x, y, width, 20),
            self.font_small)

        x, y = x, y + 2
        astro_widgets.moon_phase_axis(
            FrameBufferOffset(self.fb, x, y, width, 20),
            FrameBufferFont("fonts/LiberationSans-Bold.14.mfnt", palette=self.palette_white),
            x_padding=2)


        # Precipitation part:
        x, y = x, 330
        PrecipitationStrip(data['astro'], self.colors).draw(
            FrameBufferOffset(self.fb, x, y, width, height),
            self.font_small,
            data['precipitation']['time'],
            data['precipitation']['values'],
            data['meteofcst']['time'],
            data['meteofcst']['precipitation']['average'])

        # Temperature part:
        x, y = x, 270
        TemperatureStrip(data['astro'], self.colors).draw(
            FrameBufferOffset(self.fb, x, y, width, height),
            self.font_small,
            data['temperature']['time'],
            data['temperature']['values'],
            data['meteofcst']['time'],
            data['meteofcst']['temperature']['air'])

        # # Nothing so far:
        # logger.debug(" ============================== ")
        # chart_widget = BarPlot(self.colors.map | {'line': self.colors.BLACK, 'dot': self.colors.DARK}, self.font_small)
        # chart_widget.frame = True
        # chart_widget.axes(left=True, top=True, right=True, bottom=True)
        # chart_widget.axis_y_max = 15
        # chart_widget.axis_y_min = -5
        # chart_widget.ticks_count(bottom=13, left=5)
        # chart_widget.grid_count(horiz=5, vert=7)
        # chart_widget.grid_dash(vert=(3, 2), horiz=(3, 2))
        # chart_widget.margins(left=30, bottom=20, right=7, top=7)
        # chart_widget.ticks_per_label(bottom=2, left=1)
        # chart_widget.ticks_length(bottom=5, left=5)
        # chart_widget.dot_size = 3
        # import random
        # multi = 1
        # chart_widget.draw(FrameBufferOffset(self.fb, 10, 50, 301, 150),
        #     ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"] * multi,
        #     # [random.randint(0,150)/10 for _ in range(6)] * multi
        #     [-3, 0, 1, -5, 10, 15] * multi
        # )

        logger.debug(" ============================== ")
        # f = FrameBufferFont("fonts/LiberationSans-Bold.18.mfnt", palette=self.palette_light)
        # window = FrameBufferOffset(self.fb, 350, 70, 200, 100)
        # window.rectround(0, 0, window.width, window.height, self.colors.LIGHT, 10, True)
        # window.blit(FrameBufferExtension.fromfile("images/humidity.fb"), 10, 10, self.colors.WHITE)

        # window = FrameBufferOffset(self.fb, 20, 20, 600, 100)
        # window = self.frame(window, self.colors.LIGHT)


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
    # logging.getLogger('plot').setLevel(logging.INFO)
    logging.getLogger('plot').setLevel(logging.DEBUG)
    logging.getLogger('toolbox.framebufext').setLevel(logging.INFO)

    data = {
        'astro': json.loads(open("astro.json").read()),
        'meteo': json.loads(open("meteo.json").read()),
        'precipitation': json.loads(open("precipitation.json").read()),
        'temperature': json.loads(open("temperature.json").read()),
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
    logger.info("USED FONTS:")
    for font_file, font in meteo.FM.fonts.items():
        logger.info(f" - {font_file}")
