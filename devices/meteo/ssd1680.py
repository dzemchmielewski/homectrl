from machine import SPI, Pin
from time import sleep_ms
import framebuf
from toolbox.framebufext import FrameBufferExtension

class SSD1680:

    def __init__(self, width: int, height: int, spi: SPI, cs_pin: Pin, dc_pin: Pin, rst_pin: Pin, busy_pin: Pin, orientation: str = 'landscape'):
        self.debug = False
        self.spi = spi
        self.cs_pin, self.dc_pin, self.rst_pin, self.busy_pin = cs_pin, dc_pin, rst_pin, busy_pin

        if not orientation in ('landscape', 'portrait'):
            raise ValueError("Orientation must be 'landscape' or 'portrait'")

        self.orientation = orientation
        self.width, self.height = width, height

        if self.debug:
            print(f"Display size: {self.width} x {self.height}, orientation: {self.orientation}")
            print(f"PINS: CS={self.cs_pin}, DC={self.dc_pin}, RST={self.rst_pin}, BUSY={self.busy_pin}")

        self.reset_hw()
        self.reset_sw()

    def command(self, command: bytes, data: bytes = None):
        self.dc_pin.value(0)
        self.cs_pin.value(0)
        self.spi.write(command)
        self.cs_pin.value(1)
        if data:
            self.data(data)

    def data(self, data: bytes):
        self.dc_pin.value(1)
        self.cs_pin.value(0)
        self.spi.write(data)
        self.cs_pin.value(1)

    def reset_hw(self):
        self.rst_pin.value(1)
        # sleep_ms(200)
        sleep_ms(1_000)
        self.rst_pin.value(0)
        sleep_ms(1_000)
        # sleep_ms(200)
        self.rst_pin.value(1)
        self.wait_until_ready()
        print("Hardware reset done")

    def reset_sw(self):
        # Software Reset
        self.command(b'\x12')
        self.wait_until_ready()
        if self.debug:
            print("Software reset done")

    def wait_until_ready(self):
        sleep_ms(50)
        while self.busy_pin.value() == 1:
            sleep_ms(100)

    def display(self, fb: FrameBufferExtension, padding_byte: bytes = b'\xFF'):
        if self.busy_pin.value() == 1:
            self.reset_hw()

        # To use VLSB mode, the default display configuration need to be changed
        # to landscape. That's something I stuck with.
        # Therefore, for landscape mode, I making some additional
        # computing to rotate the framebuffer data before sending it to the display.
        # Only MONO_HLSB mode is supported for now.
        add_padding_byte = (self.width != fb.width) if fb.mode == framebuf.MONO_HLSB else (self.height != fb.height)

        print(f"Framebuffer mode: {fb.mode}, size: {fb.width} x {fb.height}, padding_byte={add_padding_byte}")
        print(f"Display mode: {self.width} x {self.height}, orientation: {self.orientation}")

        if self.orientation == 'landscape':
            buf, w, h = self.rotate_minus_90(fb)
        else:
            buf, w, h = fb.buffer, fb.width, fb.height

        self.command(b'\x24')

        if self.debug:
            print(f"Final buffer: {w} x {h}, {len(buf)} bytes")
            for b in buf:
                if b != 0x00:
                    print(f"({hex(b)})", end='')
                else:
                    print("_", end='')
            print("")

        # row by row
        bytes_per_row = w // 8
        for row in reversed(range(h)):
            start = row * bytes_per_row
            end = start + bytes_per_row
            # print(f"R{row+1}/{h}({start}-{end}) ", end='')
            self.data(buf[start:end])
            if add_padding_byte:
                self.data(padding_byte)
                if self.debug:
                    print(".", end='')


        self.command(b'\x22', b'\xF7')  # Display Update Control
        self.command(b'\x20')  # Activate Display Update

        self.wait_until_ready()

        # Enter deep sleep
        self.command(b'\x10', 'b\x01')
        sleep_ms(100)
        if self.debug:
            print(" done")

    def rotate_minus_90(self, fb: FrameBufferExtension):
        rotated = bytearray(len(fb.buffer))
        for i in range(len(rotated)):
            rotated[i] = 0

        src_bpr = fb.width // 8

        dst_w = fb.height
        dst_h = fb.width
        dst_bpr = dst_w // 8

        for y in range(fb.height):
            row_off = y * src_bpr
            for bx in range(src_bpr):
                b = fb.buffer[row_off + bx]
                if b:
                    x_base = bx * 8
                    for bit in range(8):
                        if b & (0x80 >> bit):
                            nx = y
                            ny = dst_h - 1 - (x_base + bit)
                            i = ny * dst_bpr + (nx >> 3)
                            rotated[i] |= (0x80 >> (nx & 7))
        return rotated, dst_w, dst_h


class SSD1680_2_13_in(SSD1680):

    def __init__(self, spi: SPI, cs_pin: Pin, dc_pin: Pin, rst_pin: Pin, busy_pin: Pin, orientation: str = 'landscape'):
        if not orientation in ('landscape', 'portrait'):
            raise ValueError("Orientation must be 'landscape' or 'portrait'")

        (width, height) = (250, 122) if orientation == 'landscape' else (122, 250)

        self.fb_width = (width // 8) * 8
        self.fb_height = height
        self.fb_mode = framebuf.MONO_HLSB

        super().__init__(width, height, spi, cs_pin, dc_pin, rst_pin, busy_pin, orientation=orientation)


if __name__ == "__main__":
    import json, time
    from display_meteomini import MeteoMiniDisplay
    #dev:
    # dc = Pin(3, Pin.OUT)
    # rst = Pin(4, Pin.OUT)
    # cs = Pin(2, Pin.OUT)
    # busy = Pin(21, Pin.IN, Pin.PULL_DOWN)
    # spi = SPI(1, baudrate=10000000, sck=Pin(1), mosi=Pin(0))

    #meteo:
    dc = Pin(2, Pin.OUT)
    rst = Pin(3, Pin.OUT)
    cs = Pin(1, Pin.OUT)
    busy = Pin(4, Pin.IN)
    nothing=Pin(6)
    spi = SPI(1, baudrate=1_000_000, sck=Pin(0), mosi=Pin(21))

    landscape = True
    if landscape:
        ssd = SSD1680_2_13_in(spi, cs, dc, rst, busy, orientation='landscape')
    else:
        ssd = SSD1680_2_13_in(spi, cs, dc, rst, busy, orientation='portrait')

    print (f"Framebuffer: {ssd.fb_width} x {ssd.fb_height}, mode={ssd.fb_mode}")
    meteo = MeteoMiniDisplay(ssd.fb_width, ssd.fb_height, ssd.fb_mode)
    temperature = round(time.localtime()[4] + (time.localtime()[5]/100), 1)
    astro_data = json.loads('{"name": "astro", "astro": [{"date": "2025-11-03", "weekday": "Monday", "sun": {"event": [{"type": "rise", "time": "06:47:17"}, {"type": "set", "time": "16:10:14"}]}, "moon": {"event": [{"type": "rise", "time": "15:00:46"}, {"type": "set", "time": "03:38:23"}], "phase": 0.43}}, {"date": "2025-11-04", "weekday": "Tuesday", "sun": {"event": [{"type": "rise", "time": "06:49:10"}, {"type": "set", "time": "16:08:24"}]}, "moon": {"event": [{"type": "rise", "time": "15:13:59"}, {"type": "set", "time": "05:10:44"}], "phase": 0.46}}, {"date": "2025-11-05", "weekday": "Wednesday", "sun": {"event": [{"type": "rise", "time": "06:51:03"}, {"type": "set", "time": "16:06:35"}]}, "moon": {"event": [{"type": "rise", "time": "15:31:33"}, {"type": "set", "time": "06:47:53"}], "phase": 0.5}}, {"date": "2025-11-06", "weekday": "Thursday", "sun": {"event": [{"type": "rise", "time": "06:52:56"}, {"type": "set", "time": "16:04:47"}]}, "moon": {"event": [{"type": "rise", "time": "15:56:57"}, {"type": "set", "time": "08:27:59"}], "phase": 0.53}}, {"date": "2025-11-07", "weekday": "Friday", "sun": {"event": [{"type": "rise", "time": "06:54:48"}, {"type": "set", "time": "16:03:02"}]}, "moon": {"event": [{"type": "rise", "time": "16:36:16"}, {"type": "set", "time": "10:03:41"}], "phase": 0.56}}, {"date": "2025-11-08", "weekday": "Saturday", "sun": {"event": [{"type": "rise", "time": "06:56:41"}, {"type": "set", "time": "16:01:18"}]}, "moon": {"event": [{"type": "rise", "time": "17:36:15"}, {"type": "set", "time": "11:22:53"}], "phase": 0.6}}, {"date": "2025-11-09", "weekday": "Sunday", "sun": {"event": [{"type": "rise", "time": "06:58:33"}, {"type": "set", "time": "15:59:37"}]}, "moon": {"event": [{"type": "rise", "time": "18:54:22"}, {"type": "set", "time": "12:17:38"}], "phase": 0.63}}], "datetime": {"date": "2025-11-04", "time": "23:07:03.481179", "weekday": "Tuesday"}}')
    meteo_data = json.loads('{"temperature": -' + str(temperature)+ ', "humidity": 93.0, "pressure": {"real": 1018.5, "sea_level": 1024.7}, "precipitation": 0.0, "wind": {"speed": 0.7, "direction": 100, "direction_desc": "E", "max": {"speed": 1.6, "direction": 158, "direction_desc": "S"}}, "solar_radiation": 0.0, "date": "2025-11-05T02:24:18+01:00", "create_at": "2025-11-05T02:25:01.775631"}')
    meteo.update(meteo_data, astro_data)

    ssd.display(meteo.fb)


