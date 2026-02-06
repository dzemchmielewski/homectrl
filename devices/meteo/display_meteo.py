if __name__ == "__main__":
    import sys
    sys.path.append('../../micropython')
    sys.path.append('../../devel')
    import logging
    logging.basicConfig(level=logging.DEBUG)

import random
import framebuf
import json
import time
from meteoparts.astropart import AstroPart
from meteoparts.temperaturestrip import TemperatureStrip
from meteoparts.precipitationstrip import PrecipitationStrip
from plot import *
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont, FrameBufferOffset, FM
from colors import Colors

class MeteoDisplay:

    FRAME_THICKNESS = 5

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

        # self.font_battery = FrameBufferFont("fonts/LiberationSans-Bold.14.mfnt", palette=self.palette_light)
        # self.font_serif_bold_52 = FrameBufferFont("fonts/LiberationSerif-Bold.52.mfnt", palette=self.palette_white)
        # self.font_sans_bold_26 = FrameBufferFont("fonts/LiberationSans-Bold.26.mfnt", palette=self.palette_white)

        # self.fonts_middle = FrameBufferFont("fonts/LiberationSerif-Bold.52.mfnt", palette=self.palette_white)
        # self.font_topbottom = FrameBufferFont("fonts/LiberationSans-Bold.18.mfnt", palette=self.palette_white)
        # self.font_hour = FrameBufferFont("fonts/LiberationMono-Italic.12.mfnt", palette=self.palette_white)
        # self.font_small = FrameBufferFont("fonts/LiberationSans-Bold.12.mfnt", palette=self.palette_white)


    def palette(self, colors: list):
        # index 0 - background, index 1 - foreground, others - shades
        return FrameBufferExtension.palette(colors, self.fb.mode)

    def frame(self, fb: FrameBufferExtension, border = None, background = None):
        if border is None:
            border = self.colors.LIGHT
        if background is None:
            background = self.colors.WHITE
        thickness, radius = MeteoDisplay.FRAME_THICKNESS, [12, 9]
        fb.rectround(0, 0, fb.width, fb.height, border, radius[0], True)
        fb.rectround(thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness, background, radius[1], True)
        return FrameBufferOffset(fb, thickness, thickness, fb.width - 2 * thickness, fb.height - 2 * thickness)

    def _small_item(self, fb, x, y, w, h, image, text: str):
        fb = FrameBufferOffset(fb, x, y, w, h)
        fb.rectround(0, 0, w, h, self.colors.LIGHT, 6, True)
        gap = 10
        fb.blit(FrameBufferExtension.fromfile(image), gap, 3, self.colors.WHITE)
        gap += 16
        f = FrameBufferOffset(fb, gap, 0, w - gap, h)
        #f.fill(self.colors.LIGHT)
        f.textfalign(text, FM.get_sans_bold(16), top_margin=-2, palette=self.palette_light)
        return x + w, y + h

    def battery(self, fb, x, y, w, h, level_percent: int):
        return self._small_item(fb, x, y, w, h,
                                'images/battery-quarter.fb' if level_percent <= 25 else (
                                    'images/battery-half.fb' if level_percent <= 50 else (
                                        'images/battery-three-quarters.fb' if level_percent <= 75 else 'images/battery-full.fb')),
                                str(level_percent) + "%")

    def source(self, fb, x, y, w, h, source: str):
        return self._small_item(fb, x, y, w, h, 'images/source.fb', source)

    def time(self, fb, x, y, w, h, time_str: str):
        return self._small_item(fb, x, y, w, h, 'images/time.fb', time_str)

    def _meteo_item(self, fb, x, y, image_file: str, text: str, font: FrameBufferFont, width: int, top_margin: int = 11, left_margin: int = 0, unit: str = None):
        image = FrameBufferExtension.fromfile(image_file)
        w, h = width, image.height + 2*10 + 2*5
        window = FrameBufferOffset(fb, x, y, w, h)
        window = self.frame(window)
        window.blit(image, 5, 10, self.colors.WHITE)

        # tw, th = font.size(text)
        # tw, th = tw + 6, th + 10
        # textframe = window.rectround(image.width + 2*5, (window.height - th) // 2, tw, th, self.colors.LIGHT, 8, True)

        textframe = FrameBufferOffset(window,  image.width, window.height // 4, window.width - (image.width + 2*5), window.height//2)
        if unit is not None:
            top_margin = -3
        textframe.textfalign(text, font, top_margin=top_margin, left_margin=left_margin, palette=self.palette_white)

        if unit:
            textframe = FrameBufferOffset(window,  image.width, textframe.height + 5, window.width - (image.width + 2*5), 25)
            textframe.textfalign(unit, FM.get_sans_bold(14), left_margin=left_margin)

        return x + w, y + h

    def temperature(self, fb, x, y, temperature: float):
        return self._meteo_item(fb, x, y, "images/temperature.fb", "{:2.1f}".format(temperature) + "°C", FM.get_serif_bold(52), 285)

    def humidity(self, fb, x, y, humidity: int):
        return self._meteo_item(fb, x, y, "images/humidity.fb", str(humidity), FM.get_sans_bold(26), 140, unit="%")

    def pressure(self, fb, x, y, pressure: float):
        x, y = self._meteo_item(fb, x, y, "images/pressure.fb", "{:4.1f}".format(pressure), FM.get_sans_bold(26), 140, unit="hPa", left_margin=14)
#        fb.textf("hPa", x - 40, y - 20, FM.get_sans_bold(14))
        return x, y

    def wind(self, fb, x, y, speed: float):
        x, y = self._meteo_item(fb, x, y, "images/wind.fb", "{:4.1f}".format(speed), FM.get_sans_bold(26), 140, unit="m/s")
        return x, y

    def direction(self, fb, x, y, direction: str, angle: int):
        return self._meteo_item(fb, x, y, "images/compass.fb", direction, FM.get_sans_bold(26), 140, unit=str(angle) + "°")

    def calendar(self, fb, _x, _y, _w, _h, date: str, weekday: str):
        image = FrameBufferExtension.fromfile("images/weekday.fb")
        window = FrameBufferOffset(fb, _x, _y, _w, _h)
        window = self.frame(window)
        window.blit(image, 10, 19, self.colors.WHITE)

        x, y = image.width, 10
        f = FrameBufferOffset(window,  x, y, window.width - (image.width + 2*5), 50)
        _, y = f.textfalign(weekday, FM.get_serif_bold(60), top_margin=-10, left_margin=5)
        y += -25

        f = FrameBufferOffset(window,  x, y, window.width - (image.width + 2*5), 50)
        _, y = f.textfalign(date, FM.get_sans_bold(38), top_margin=5)

        return _x + _w, _y + _h

    @staticmethod
    def _add_word(line: str, word: str) -> str:
        return f"{line}{" " if line != "" else ""}{word}"

    def _split_text(self, text: str, font: FrameBufferFont, max_width: int) -> tuple(str, str):
        tw, _ = font.size(text)
        line, rest = "", None
        if tw > max_width:
            words = text.split(" ")
            for idx, word in enumerate(words):
                next = self._add_word(line, word)
                tw, _ = font.size(next)
                if tw <= max_width:
                    line = next
                else:
                    rest = ""
                    for i in range(idx, len(words)):
                        rest = f"{rest}{' ' if rest != '' else ''}{words[i]}"
                    break
        else:
            line = text
        return line, rest

    def holiday(self, fb, x, y, w, h, holidays: list):
        text = holidays[random.randint(0, len(holidays)-1)]
        window = FrameBufferOffset(fb, x, y, w, h)
        window = self.frame(window)
        window = FrameBufferOffset(window, 10, 10, window.width - 2*10, window.height - 2*10)
        # window.fill(self.colors.LIGHT)

        font = FM.get_sans_bold(32)
        lines = []
        while True:
            line, rest = self._split_text(text, font, window.width)
            lines.append(line)
            if rest is None:
                break
            text = rest

        if len(lines) == 1:
            _, h = window.textfalign(lines[0],  font)
        elif len(lines) == 2:
            m = 40
            window.textfalign(lines[0], font, top_margin=-m)
            window.textfalign(lines[1], font, top_margin=m)
        else:
            m = 65
            window.textfalign(lines[0], font, top_margin=-m)
            window.textfalign(lines[1], font, top_margin=-2)
            window.textfalign(lines[2], font, top_margin=m)

        return x + w, y + h


    # Sun & Moon calendar widget:
    def  sunmoon(self, fb,  x, y, width, height, data: dict):
        # width, height = 760, 83
        astro_widgets = AstroPart(data['astro'], self.colors)
        #fb.rectround(x, y, width, height, self.colors.BLACK, 10, True)
        d = MeteoDisplay.FRAME_THICKNESS + 2
        self.frame(FrameBufferOffset(fb, x, y, width, height), self.colors.BLACK, self.colors.WHITE)

        width -= 2 * d + 2
        x, y = x + d, y + d
        _, y = astro_widgets.weekday_axis(
            FrameBufferOffset(fb, x, y, width, 20),
            FM.get_sans_bold(16))

        x, y = x, y + 5
        astro_widgets.sun_axis(
            FrameBufferOffset(fb, x, y, width, 20),
            FM.get_sans_bold(12))

        x, y = x, y + 19
        _, y = astro_widgets.moon_axis(
            FrameBufferOffset(fb, x, y, width, 20),
            FM.get_sans_bold(12))

        x, y = x, y + 2
        astro_widgets.moon_phase_axis(
            FrameBufferOffset(fb, x, y, width, 20),
            FM.get_sans_bold(14),
            x_padding=2)
        return x, y

    def past_and_forecst(self, fb, x, y, width, height, data: dict):
        d = MeteoDisplay.FRAME_THICKNESS + 2
        off_x, off_y = 13, 4 # additional offset for scale, that has to be out of buffer frame
        width_off = 8 # additional width cut from the right for scale labels
        self.frame(FrameBufferOffset(fb, x, y, width, height), self.colors.BLACK, self.colors.WHITE)

        fb.blit(FrameBufferExtension.fromfile('images/temperature-16.fb'), x+d, y + d + 15, self.colors.WHITE)
        off_x, off_y = off_x + 16, off_y

        # PrecipitationStrip(data['astro'], self.colors).draw(
        #     FrameBufferOffset(self.fb, x + d + off_x, y + d + off_y, width - 2*d, height - 2*d),
        #     FM.get_sans_bold(12),
        #     data['precipitation']['time'],
        #     data['precipitation']['values'],
        #     data['meteofcst']['time'],
        #     data['meteofcst']['precipitation']['average'])

        # # Temperature part:
        TemperatureStrip(data['astro'], self.colors).draw(
            FrameBufferOffset(self.fb, x + d + off_x, y + d + off_y, width - 2*d - off_x - width_off, height - 2*d),
            FM.get_sans_bold(12),
            data['temperature']['time'],
            data['temperature']['values'],
            data['meteofcst']['time'],
            data['meteofcst']['temperature']['air'])


    def update(self, data: dict):
        self.fb.fill(self.colors.LIGHT)

        # Main meteo part:
        margin = 2
        inner_space, inner_margin = 5, 10
        w, h = 285 + 2*inner_margin, 252 + 2*inner_margin

        x, y = margin, margin
        window = self.fb.rectround(x, y, w, h, self.colors.BLACK, 10, True)

        x, y = inner_margin + self.FRAME_THICKNESS, inner_margin
        x, y = self.battery(window, x, y, 73, 22, data['battery'])
        x, y = x + inner_space, inner_margin
        x, y = self.source(window, x, y, 118, 22, data['meteo']['source'])
        x, y = x + inner_space, inner_margin
        x, y = self.time(window, x, y, 74, 22, f"{data['meteo']['date'][11:13]}:{data['meteo']['date'][14:16]}")

        x, y  = inner_margin, y + inner_space
        x, y = self.temperature(window, x, y, data['meteo']['temperature'])
        x, y =  inner_margin, y + inner_space
        x, _ = self.humidity(window, x, y, data['meteo']['humidity'])
        x += inner_space
        x, y = self.pressure(window, x, y, data['meteo']['pressure']['real'])
        x, y = inner_margin, y + inner_space
        x, _ = self.wind(window, x, y, data['meteo']['wind']['speed'])
        x += inner_space
        x, y = self.direction(window, x, y, data['meteo']['wind']['direction_desc'], data['meteo']['wind']['direction'])

        # Calendar part:
        thedate = time.strftime("%B %e, %Y",
                                time.localtime(
                                    time.fromisostrict(data['astro']['datetime']['date'])))
        x, y = margin + w + 5, margin
        w, h = self.fb.width - x - margin, 252 + 2*inner_margin
        window = self.fb.rectround(x, y, w, h, self.colors.BLACK, 10, True)
        x, y = inner_margin, inner_margin
        w, h = w - 2*inner_margin, ((h - 2*inner_margin) // 2) - inner_space // 2
        _, y = self.calendar(window, x, y, w, h,thedate, data['astro']['datetime']['weekday'])
        y += inner_space
        x, y = self.holiday(window, x, y, w, h, data['holidays']['holidays'])


        x, y, w, h  = 2, 380, self.fb.width - 2 * 2, 98
        self.sunmoon(self.fb, x, y, w, h, data)

        # Temperature and precipitation history/forecast:
        x, y = x, 278
        self.past_and_forecst(self.fb, x, y, w, h, data)


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
    logger = logging.getLogger("meteo_display")
    # logging.getLogger('plot').setLevel(logging.INFO)
    logging.getLogger('plot').setLevel(logging.DEBUG)
    logging.getLogger('toolbox.framebufext').setLevel(logging.INFO)


    import time
    #minutes = time.localtime()[4]
    minutes = 100

    data = {
        'astro': json.loads(open("astro.json").read()),
        'meteo': json.loads(open("meteo.json").read()),
        'precipitation': json.loads(open("precipitation.json").read()),
        'temperature': json.loads(open("temperature.json").read()),
        'meteofcst': json.loads(open("meteofcst.json").read())['meteofcst'],
        'holidays': json.loads(open("holidays.json").read()),
        'battery': minutes,
    }

    # Mangling data:
    from_day_offset = -1
    to_day_offset = 4

    # Astro:
    # Pick only 5 days of astro data:
    data['astro']['astro'] = [astro_data for astro_data in data['astro']['astro'] if astro_data['day']['day_offset'] in range(from_day_offset, to_day_offset)]
    logger.debug(f"Astro data: {data['astro']}")


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
    for font_file, font in FM.cache.items():
        logger.info(f" - {font_file}")
