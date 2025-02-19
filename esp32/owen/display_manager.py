import asyncio
import time

import st7789
from micropython import const

import config
import board.board_shared as shared

class Part:
    def __init__(self, name):
        self.name = name
        self.has_on_event = False
        self.has_on_touch = False


class PartialDisplay(Part):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        super().__init__(cfg[config.CFG_NAME])
        self.display = display
        self.x, self.y, self.width, self.height = (
            cfg[config.CFG_X], cfg[config.CFG_Y], cfg[config.CFG_WIDTH], cfg[config.CFG_HEIGHT])

    @staticmethod
    def int2digits(number, size, empty_zero = True, last_zero = True):
        digits = [None] * size
        for i in range(size):
            digits[size - i - 1] = (number // pow(10, i)) % 10
        if empty_zero:
            for i in range(size - 1 if last_zero else size):
                if digits[i] == 0:
                    digits[i] = 10
                else:
                    break
        return digits


class Clickable(Part):
    IDLE = const(0)
    TAP_STARTED = const(1)
    LONG_CLICK = const(800)

    def __init__(self, display, cfg: dict):
        super().__init__(cfg.get(config.CFG_NAME))
        self.has_on_touch = True
        self.touch_x, self.touch_y, self.touch_width, self.touch_height = (
            cfg.get(config.CFG_TOUCH_X, cfg.get(config.CFG_X)),
            cfg.get(config.CFG_TOUCH_Y, cfg.get(config.CFG_Y)),
            cfg.get(config.CFG_TOUCH_WIDTH, cfg.get(config.CFG_WIDTH)),
            cfg.get(config.CFG_TOUCH_HEIGHT, cfg.get(config.CFG_HEIGHT)))
        self.status = self.IDLE
        self.on_me_time_ms = None
        self.event_recipient = cfg.get(config.CFG_EVENT_RECIPIENT)

    def set_status(self, status):
        if self.status != status:
            self.status = status

    def on_touch(self, event: shared.DataEvent):
        result = None
        x, y = event['point'][0][0:2]
        on_me = self.touch_x <= x <= self.touch_x + self.touch_width and self.touch_y <= y <= self.touch_y + self.touch_height

        if on_me:
            if self.status == self.IDLE:
                if event['type'] == 'tap-in':
                    self.set_status(self.TAP_STARTED)
                    self.on_me_time_ms = time.ticks_ms()
                # When IDLE, tap-move and tap-out are ignored

            elif self.status == self.TAP_STARTED:
                if event['type'] == 'tap-out':
                    self.set_status(self.IDLE)
                    result = {'type': 'click-short' if event['time'] < self.LONG_CLICK else 'click-long'}

                elif event['type'] in ('tap-keep', 'tap-move'):
                    if time.ticks_ms() - self.on_me_time_ms > self.LONG_CLICK:
                        self.on_me_time_ms = time.ticks_ms()
                        result = {'type': 'click-keep'}

        else: # not on me
            if self.status == self.IDLE:
                pass
            elif self.status == self.TAP_STARTED:
                # Started on me, but finished out of me, so:
                # - no result returned
                # - back the status to idle
                if event['type'] == 'tap-out':
                    self.set_status(self.IDLE)
                else:
                    self.on_me_time_ms = time.ticks_ms()

        return result



class Button(PartialDisplay, Clickable):

    def __init__(self, display:st7789.ST7789, cfg: dict):
        PartialDisplay.__init__(self, display, cfg)
        Clickable.__init__(self, display, cfg)
        self.has_on_event = True
        self.images = {
            name:[
                self.display.jpg_decode(file[0], 0, 0, self.width, self.height)[0],
                self.display.jpg_decode(file[1], 0, 0, self.width, self.height)[0]]
            for name,file in cfg[config.CFG_IMAGE].items()}
        self.label = cfg[config.CFG_DEFAULT_LABEL]
        self._draw()

    def set_status(self, status):
        super().set_status(status)
        self._draw()

    def _set_label(self, label):
        if self.label != label:
            self.label = label
            self._draw()

    def _draw(self):
        self.display.blit_buffer(
            self.images[self.label][1] if self.status == Button.IDLE else self.images[self.label][0],
            self.x, self.y, self.width, self.height)


    def on_event(self, event: dict):
        if (label := event.get('label')) is not None:
            self._set_label(label)


class TemperatureDisplay(PartialDisplay):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        super().__init__(display, cfg)
        self.has_on_event = True
        self.img_digits = [
            self.display.jpg_decode(cfg[config.CFG_IMAGE], i * self.width, 0, self.width, self.height)[0]
            for i in range(12)]

    def on_event(self, event: dict):
        digits = self.int2digits(event['value'], 3) if event['value'] else [11] * 3
        for i in range(3):
            self.display.blit_buffer(self.img_digits[digits[i]], self.x + i * self.width, self.y, self.width, self.height)
        return None


class TimeDisplay(PartialDisplay):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        pass

    def on_event(self, data: shared.DataEvent):
        pass
        # if data['value'] != self.last:
        #     for i in range(3):
        #         if data['value'][i] != self.last[i]:
        #             digits = self.int2digits(data['value'][i], 2, False)
        #             for j in range(2):
        #                 pos = self.x  + (i * 2 * self.width) + (i * self.dots_width) + (j * self.width)
        #                 self.display.blit_buffer(self.img_digits[digits[j]], pos, self.y, self.width, self.height)
        #     self.last = data['value']


class TimerDisplay(PartialDisplay):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        super().__init__(display, cfg)
        self.has_on_event = True
        self.dots_width = 5
        self.dots_height = 16
        self.img_digits = [
            self.display.jpg_decode(cfg[config.CFG_IMAGE], i * self.width, 0, self.width, self.height)[0] for i in range(11)]
        self.img_dots = [
            self.display.jpg_decode(cfg['image-dots'], i * self.dots_width, 0, self.dots_width, self.dots_height)[0] for i in range(2)]
        self.last = (None, None, None)

    def on_event(self, event: dict):
        value = event['value']
        if value != self.last:
            for i in range(3):
                if value[i] != self.last[i]:
                    digits = self.int2digits(value[i], 2, i == 0 or value[i - 1] == 0, False)
                    for j in range(2):
                        pos = self.x  + (i * 2 * self.width) + (i * self.dots_width) + (j * self.width)
                        self.display.blit_buffer(self.img_digits[digits[j]], pos, self.y, self.width, self.height)
                    if i < 2:
                        pos = self.x  + ((i+1) * 2 * self.width) + (i * self.dots_width)
                        self.display.blit_buffer(self.img_dots[1 if value[i] > 0 else 0], pos, self.y, self.dots_width, self.dots_height)
            self.last = value


class SetButtonDisplay(PartialDisplay):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        super().__init__(display, cfg)
        self.images = {
            name: self.display.jpg_decode(file, 0, 0, self.width, self.height)[0]
            for name,file in cfg[config.CFG_IMAGE].items()}
        self.label = cfg[config.CFG_DEFAULT_LABEL]
        self._draw()

    def _set_label(self, label):
        if self.label != label:
            self.label = label
            self._draw()

    def _draw(self):
        self.display.blit_buffer(
            self.images[self.label], self.x, self.y, self.width, self.height)

    def on_event(self, event: dict):
        if (label := event.get('label')) is not None:
            self._set_label(label)


class ModeButton(SetButtonDisplay, Clickable):
    def __init__(self, display:st7789.ST7789, cfg: dict):
        SetButtonDisplay.__init__(self, display, cfg)
        Clickable.__init__(self, display, cfg)


class DisplayManager(shared.EventConsumer, shared.EventEmitter):
    def __init__(self, display: st7789.ST7789):
        shared.EventConsumer.__init__(self, 'display')
        shared.EventEmitter.__init__(self, 'display')
        self.display = display
        self.display.init()
        self.display.jpg(config.IMG_BACKGROUND, 0, 0, st7789.FAST)
        self.last_action_time = time.ticks_ms()
        self.is_dimmed = False
        self.allow_dim = True

        self._dim_task = asyncio.create_task(self._dim())
        self.part_names = [cfg['name'] for cfg in config.PARTS]
        self.parts = dict(zip(
            self.part_names,
            [eval(cfg[config.CFG_CLASS])(display, cfg) for cfg in config.PARTS]))

    async def consume(self, event: dict):
        if event['sender'] == 'touch':
            self.last_action_time = time.ticks_ms()
            for _, part in self.parts.items():
                if part.has_on_touch and (reaction := part.on_touch(event)) is not None:
                    reaction['sender'] = part.name
                    reaction['recipient'] = part.event_recipient if part.event_recipient else 'manager'
                    self.emit(reaction)

        elif (part_recipient := event.get('part-recipient')) is not None:
            if (part := self.parts.get(part_recipient)) is not None:
                part.on_event(event)
            else:
                raise Exception(f"Event {event} received by display but the recipient part is not known.")

        elif (dim := event.get('allow_dim')) is not None:
            self.last_action_time = time.ticks_ms()
            self.allow_dim = dim

        else:
            raise Exception(f"Event {event} received by display but not consumed.")

        return True

    def wait_for_touch(self, data: dict):
        self.dim(False)

    def dim(self, value: bool):
        self.is_dimmed = value
        self.display.off() if value else self.display.on()
        self.log.info(f"DIM: {self.is_dimmed}")
        if value:
            self.emit({
                "recipient": "touch",
                "callback": self.wait_for_touch
            })
        else:
            self.last_action_time = time.ticks_ms()


    async def _dim(self):
        def touch_active():
            return time.ticks_ms() <= self.last_action_time   +  config.SCREEN_DIM_TIME * 1_000

        while not self.exit:

            if self.allow_dim and self.is_dimmed:
                if touch_active():
                    self.dim(False)

            elif self.allow_dim and not self.is_dimmed:
                if not touch_active():
                    self.dim(True)

            elif not self.allow_dim and self.is_dimmed:
                self.dim(False)

            elif not self.allow_dim and not self.is_dimmed:
                pass

            await asyncio.sleep_ms(1_000)

    def deinit(self):
        super().deinit()
        self._dim_task.cancel()
        self.display.off()
