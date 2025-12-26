import framebuf
import json

if __name__ == "__main__":
    import sys
    sys.path.append('../../micropython')

from toolbox.framebufext import FrameBufferExtension, FrameBufferFont


class MeteoMiniDisplay:

    def __init__(self, width: int, height: int, fb_mode: int = framebuf.MONO_HLSB):
        self.fb = FrameBufferExtension(width, height, fb_mode)

        self.background = 1  # white
        # self.background = 0  # black

        if self.background == 1:
            self.palette = framebuf.FrameBuffer(bytearray(2), 1, 2, framebuf.MONO_HLSB)  # 2 entries × 1 byte each
            self.palette.pixel(0, 0, 1)  # 0 → 1
            self.palette.pixel(0, 1, 0)  # 1 → 0
        else:
            # Identity palette: 0 → 0 and 1 → 1 is default, so no need to create one.
            # Also, creating an identity palette seems  not to work correctly.
            self.palette = None
        self.foreground = self.background ^ 1

        self.fonts_middle = FrameBufferFont("LiberationSerif-Bold.52.mfnt", palette=self.palette)
        self.font_topbottom = FrameBufferFont("LiberationSans-Bold.18.mfnt", palette=self.palette)
        self.font_hour = FrameBufferFont("LiberationMono-Italic.12.mfnt", palette=self.palette)

    def _temperature(self, temperature: float) -> tuple[int, int]:
        font = self.fonts_middle

        # Render temperature
        x_spacing = 6
        temperature_str = f"{temperature:.1f}"
        size_x, size_y = font.size(f"{temperature_str}.C", x_spacing=x_spacing)
        size_x, size_y = size_x + 7, size_y  # extra for degree symbol
        x, y = self.fb.width // 2 - (size_x // 2), self.fb.height // 2 - (size_y // 2)
        x, y = self.fb.textf(f"{temperature_str}", x, y, font, key=self.background, palette=self.palette, x_spacing=x_spacing)

        # Degree symbol
        x, y = x + font.get_char('.')[2], y - font.height + round(font.height * (2/10))
        self.fb.ellipse(x, y, 6, 6, self.foreground, True)
        self.fb.ellipse(x, y, 3, 3, self.background, True)

        # "C" symbol
        x, y = x + 7, y - 10
        x, y = self.fb.textf("C", x, y, font, key=self.background, palette=self.palette)
        return x, y


    def update(self, meteo_data: dict, astro_data: dict):
        self.fb.fill(self.background)
        self._temperature(meteo_data['temperature'])

        self.fb.textf(f"{meteo_data['pressure']['real']:.1f} hPa", 10, 8, self.font_topbottom, key=self.background)

        time_str = f"{meteo_data['date'][11:13]}:{meteo_data['date'][14:16]}"
        time_str_len, _ = self.font_hour.size(time_str)
        week_length, _ = self.font_topbottom.size(astro_data['datetime']['weekday'])

        x, y = self.fb.textf(time_str,
                             self.fb.width - (10 + time_str_len + week_length), 8 + 4,
                             self.font_hour, key=self.background, palette=self.palette)
        x, y = self.fb.textf(f"{astro_data['datetime']['weekday']}",
                             x + 4, 8,
                             self.font_topbottom, key=self.background, palette=self.palette)

        precipitation = f"{meteo_data['precipitation']:.1f}mm ({meteo_data['humidity']:.0f}%)"
        self.fb.textf(precipitation, 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)

        wind = f"{meteo_data['wind']['speed']:.1f}m/s {meteo_data['wind']['direction_desc']}"
        x,y = self.font_topbottom.size(wind)
        self.fb.textf(wind, self.fb.width - x - 10, self.fb.height - (self.font_topbottom.height + 8), self.font_topbottom, key=self.background)

        #debug lines:
        # self.fb.line(0, 0, self.fb.width - 1, self.fb.height - 1, self.foreground)
        # self.fb.line(0, self.fb.height - 1, self.fb.width - 1, 0, self.foreground)

    def clear(self):
        self.fb.fill(self.background)


if __name__ == "__main__":
    import sys, time
    meteo = MeteoMiniDisplay(248, 122, framebuf.MONO_HLSB)
    temperature = round(time.localtime()[4] + (time.localtime()[5]/100), 1)
    astro_data = json.loads('{"name": "astro", "astro": [{"date": "2025-11-03", "weekday": "Monday", "sun": {"event": [{"type": "rise", "time": "06:47:17"}, {"type": "set", "time": "16:10:14"}]}, "moon": {"event": [{"type": "rise", "time": "15:00:46"}, {"type": "set", "time": "03:38:23"}], "phase": 0.43}}, {"date": "2025-11-04", "weekday": "Tuesday", "sun": {"event": [{"type": "rise", "time": "06:49:10"}, {"type": "set", "time": "16:08:24"}]}, "moon": {"event": [{"type": "rise", "time": "15:13:59"}, {"type": "set", "time": "05:10:44"}], "phase": 0.46}}, {"date": "2025-11-05", "weekday": "Wednesday", "sun": {"event": [{"type": "rise", "time": "06:51:03"}, {"type": "set", "time": "16:06:35"}]}, "moon": {"event": [{"type": "rise", "time": "15:31:33"}, {"type": "set", "time": "06:47:53"}], "phase": 0.5}}, {"date": "2025-11-06", "weekday": "Thursday", "sun": {"event": [{"type": "rise", "time": "06:52:56"}, {"type": "set", "time": "16:04:47"}]}, "moon": {"event": [{"type": "rise", "time": "15:56:57"}, {"type": "set", "time": "08:27:59"}], "phase": 0.53}}, {"date": "2025-11-07", "weekday": "Friday", "sun": {"event": [{"type": "rise", "time": "06:54:48"}, {"type": "set", "time": "16:03:02"}]}, "moon": {"event": [{"type": "rise", "time": "16:36:16"}, {"type": "set", "time": "10:03:41"}], "phase": 0.56}}, {"date": "2025-11-08", "weekday": "Saturday", "sun": {"event": [{"type": "rise", "time": "06:56:41"}, {"type": "set", "time": "16:01:18"}]}, "moon": {"event": [{"type": "rise", "time": "17:36:15"}, {"type": "set", "time": "11:22:53"}], "phase": 0.6}}, {"date": "2025-11-09", "weekday": "Sunday", "sun": {"event": [{"type": "rise", "time": "06:58:33"}, {"type": "set", "time": "15:59:37"}]}, "moon": {"event": [{"type": "rise", "time": "18:54:22"}, {"type": "set", "time": "12:17:38"}], "phase": 0.63}}], "datetime": {"date": "2025-11-04", "time": "23:07:03.481179", "weekday": "Tuesday"}}')
    meteo_data = json.loads('{"temperature": -' + str(temperature)+ ', "humidity": 93.0, "pressure": {"real": 1018.5, "sea_level": 1024.7}, "precipitation": 0.0, "wind": {"speed": 0.7, "direction": 100, "direction_desc": "E", "max": {"speed": 1.6, "direction": 158, "direction_desc": "S"}}, "solar_radiation": 0.0, "date": "2025-11-05T02:24:18+01:00", "create_at": "2025-11-05T02:25:01.775631"}')
    print(astro_data)
    print(meteo_data)
    meteo.update(meteo_data, astro_data)

    from pgmexporter import PGMExporter
    PGMExporter('/tmp/output.pgm').export_fbext(meteo.fb)
