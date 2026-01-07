import array
import logging

from colors import Colors
from toolbox.framebufext import FrameBufferExtension, FrameBufferFont

log = logging.getLogger(__name__)

class AstroPart:

    def __init__(self, astro: dict, monochrome_scale: Colors):
        self.astro = astro
        self.colors = monochrome_scale
        self.days_count = len(self.astro['astro'])

    def weekday_axis(self, fb: FrameBufferExtension, font: FrameBufferFont = None, border = False, x_padding = 0):
        day_length = fb.width // self.days_count
        log.info("day_length=%d, fb.width=%d, days_count=%d", day_length, fb.width, self.days_count)
        today = self.astro['datetime']['weekday']
        x, y = 0, 0

        for astro_day_index, astro_day in enumerate(self.astro['astro']):
            day_name = astro_day['day']['weekday']

            if border:
                fb.rect(astro_day_index * day_length + x_padding, 0, day_length - 2 * x_padding, fb.height, self.colors.BLACK, False)

            if day_name == today:
                fb.rect(astro_day_index * day_length + (1 if border else  0) + x_padding, 1 if border else 0,
                        day_length - (2 if border else 0) - 2 * x_padding, fb.height - (2 if border else 0),
                        self.colors.DARK, True)

            size_x, size_y = font.size(day_name)
            x = astro_day_index * day_length + (day_length // 2) - (size_x // 2)
            y = (fb.height // 2) - (size_y // 2)
            if day_name == today:
                x, y = fb.textf(day_name, x, y, font, key=self.colors.BLACK, invert_colors=True)
            else:
                x, y = fb.textf(day_name, x, y, font, key=self.colors.WHITE)
        return x, y

    def sun_axis(self, fb: FrameBufferExtension, font: FrameBufferFont):
        day_length = fb.width // self.days_count

        intervals = []
        for astro_day_index, astro_day in enumerate(self.astro['astro']):
            events = [e for e in astro_day['sun']['events'] if e['type'] in ('rise', 'set')]
            events.sort(key=lambda e: e['time'])  # Ensure chronological order

            # Calculate x positions for all events
            event_xs = []
            for e in events:
                hour, minute, _ = e['time'].split(':')
                hour, minute = int(hour), int(minute)
                x = astro_day_index * day_length + (hour * 60 + minute) * day_length // 1440
                event_xs.append((e['type'], x))

            # Determine intervals when the sun is up
            if events:
                for i in range(0, len(event_xs) - 1, 2):
                    if event_xs[i][0] == 'rise' and event_xs[i+1][0] == 'set':
                        intervals.append((event_xs[i][1], event_xs[i+1][1], events[i]['time'], events[i+1]['time']))

        # Calculations done, now drawing

        # draw a horizontal line at the bottom:
        fb.line(0, fb.height - 1, fb.width, fb.height - 1, self.colors.foreground)

        # Draw trapezoids for sun rise/set intervals
        h = (fb.height - 3) // 2  # '-3' because of lines and spacing
        up = fb.height - h - 1
        for x0, x1, rise, set in intervals:
            #self.fb.rect(x0, up, x1 - x0, h, self.scale.foreground, True)
            points = array.array('I',
                                 [x0, up + h,
                                  x1, up + h,
                                  x1 + (- h if set is not None else 0), up ,
                                  x0 + (h if rise is not None else 0), up ])
            fb.poly(0, 0, points, self.colors.LIGHT, True)

            # Draw rise/set times
            self._put_time(fb, font, x0, up - 12, rise)
            self._put_time(fb, font, x1, up - 12, set)

        # Draw a vertical line to separate days:
        for astro_day_index in range(1, self.days_count):
            fb.vline(astro_day_index * day_length, fb.height // 2, fb.height // 2, self.colors.foreground)


    def moon_axis(self, fb: FrameBufferExtension, font: FrameBufferFont):
        day_length = fb.width // self.days_count

        intervals = []
        for astro_day_index, astro_day in enumerate(self.astro['astro']):
            events = [e for e in astro_day['moon']['events'] if e['type'] in ('rise', 'set')]
            events.sort(key=lambda e: e['time'])  # Ensure chronological order

            # Calculate x positions for all events
            event_xs = []
            for e in events:
                hour, minute, _ = e['time'].split(':')
                hour, minute = int(hour), int(minute)
                x = astro_day_index * day_length + (hour * 60 + minute) * day_length // 1440
                event_xs.append((e['type'], x))

            # Determine intervals when the moon is up
            if events:
                if events[0]['type'] == 'set':
                    # Moon is up at the start of the day
                    intervals.append((astro_day_index * day_length, event_xs[0][1], None, events[0]['time']))
                    event_xs = event_xs[1:]
                # Pair up rise/set events
                for i in range(0, len(event_xs) - 1, 2):
                    if event_xs[i][0] == 'rise' and event_xs[i+1][0] == 'set':
                        intervals.append((event_xs[i][1], event_xs[i+1][1], events[i]['time'], events[i+1]['time']))
            # If the last event is a rise, moon stays up till end of day
            if events and events[-1]['type'] == 'rise':
                intervals.append((event_xs[-1][1], (astro_day_index + 1) * day_length, events[-1]['time'], None))

        # Join intervals that are contiguous
        if intervals:
            merged = [intervals[0]]
            for start, end, rise, set in intervals[1:]:
                last_start, last_end, last_rise, last_set = merged[-1]
                if last_end == start:
                    merged[-1] = (last_start, end, last_rise, set)
                else:
                    merged.append((start, end, rise, set))
            intervals = merged

        # Calculations done, now drawing
        x, y = 0, 0

        # draw a horizontal line at the top:
        fb.line(0, 0, fb.width, 0, self.colors.foreground)

        # Draw trapezoids for moon rise/set intervals
        h = (fb.height - 3) // 2  # '-3' because of lines and spacing
        up = 1
        for x0, x1, rise, set in intervals:
            #self.fb.rect(x0, up, x1 - x0, h, self.scale.foreground, True)
            points = array.array('I',
                                 [x0, up,
                                  x1, up,
                                  x1 + (- h if set is not None else 0), up + h ,
                                  x0 + (h if rise is not None else 0), up + h])
            fb.poly(0, 0, points, self.colors.DARK, True)

            # Draw rise/set times
            rx, ry = self._put_time(fb, font, x0, up + h + 2, rise)
            x, y = (rx, ry) if rx and ry else (x, y)
            rx, ry = self._put_time(fb, font, x1, up + h + 2, set)
            x, y = (rx, ry) if rx and ry else (x, y)

        # Draw a vertical line to separate days:
        for astro_day_index in range(1, self.days_count):
            fb.vline(astro_day_index * day_length, 0, fb.height // 2, self.colors.foreground)

        return x, y

    def moon_phase_axis(self, fb: FrameBufferExtension, font: FrameBufferFont, x_padding = 0):
        day_length = fb.width // self.days_count

        for astro_day_index, astro_day in enumerate(self.astro['astro']):
            phase = astro_day['moon']['phase']

            event = None
            for _event in astro_day['moon']['events']:
                if _event['type'] == 'phase':
                    event = _event

            # Convert phase (0.0 - 1.0) to percent of illumination
            illumination = f"{(1 - abs(phase - 0.5) * 2) * 100:.0f}%"
            size_x, size_y = font.size(illumination)

            log.debug(f"{astro_day['day']['weekday']}: phase={phase}, event={event}, illumination={illumination}")

            fb.rect(astro_day_index * day_length + x_padding, 0, day_length - 2 * x_padding, fb.height - 3, self.colors.LIGHT if event else self.colors.DARK, True)

            event_size = 6
            x = astro_day_index * day_length + (day_length // 2) - (size_x // 2) - (0 if event is None else (event_size // 2 + 2))

            y = (fb.height - 2) // 2 - (size_y // 2)
            if event:
                x, _ = fb.textf(illumination, x, y, font, self.colors.WHITE)
            else:
                x, _ = fb.textf(illumination, x, y, font, self.colors.BLACK, invert_colors=True)
            self.draw_moon_phase_event(fb, x + 6, (fb.height - 3)// 2, event_size, event, phase)


    @staticmethod
    def _put_time(fb: FrameBufferExtension, font: FrameBufferFont, x: int, y: int, time_str: str) -> tuple[int, int]:
        if time_str is not None:
            size_x, size_y = font.size(time_str[0:5])
            return fb.textf(time_str[0:5], x - (size_x // 2), y, font, -1)
        return None, None

    def draw_moon_phase_event(self, fb: FrameBufferExtension, x: int, y: int, size: int, event: dict, phase: float = 0.0):
        if event and event.get('name') == 'new_moon':
            # Draw a filled black circle
            fb.ellipse(x, y, size, size, self.colors.BLACK, True)
        elif event and event.get('name') == 'full_moon':
            # Draw a filled white circle
            fb.ellipse(x, y, size, size, self.colors.WHITE, True)
        elif (event and event.get('name') == '1st_quarter') or (0.0 <= phase < 0.5):
            fb.ellipse(x, y, size, size, self.colors.WHITE, True, 0b1001)
            fb.ellipse(x, y, size, size, self.colors.BLACK, True, 0b0110)
        elif (event and event.get('name') == '4th_quarter') or (0.5 <= phase <= 1.0):
            fb.ellipse(x, y, size, size, self.colors.WHITE, True, 0b0110)
            fb.ellipse(x, y, size, size, self.colors.BLACK, True, 0b1001)



