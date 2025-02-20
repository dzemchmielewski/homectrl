import asyncio
import time
try:
    from micropython import const
except ImportError:
    def const(value):
        return value


class Timer:

    class LoopedList(list):
        def next(self, to_element):
            return self[(self.index(to_element) + 1) % len(self)]

    TIMER_STATUS_IDLE = const('idle')
    TIMER_STATUS_ON = const('on')

    TIMER_MODE_TIMER = const('timer')
    TIMER_MODE_STOPWATCH = const('stopwatch')
    TIMER_MODE = LoopedList([TIMER_MODE_TIMER, TIMER_MODE_STOPWATCH])

    TIMER_SET_CONTEXT_HOUR = const('hour')
    TIMER_SET_CONTEXT_MIN = const('min')
    TIMER_SET_CONTEXT_SEC = const('sec')
    TIMER_SET_CONTEXT = [TIMER_SET_CONTEXT_HOUR, TIMER_SET_CONTEXT_MIN, TIMER_SET_CONTEXT_SEC]

    def __init__(self, tick_callback = None, done_callback = None):
        self.timer_value = 0
        self.current_value = 0

        self.setup_context = Timer.TIMER_SET_CONTEXT_MIN
        self.status = Timer.TIMER_STATUS_IDLE
        self.mode = Timer.TIMER_MODE_TIMER

        self.tick_callback = tick_callback
        self.done_callback = done_callback
        self._tick_task = None

    async def _tick(self):
        last = time.time() % 1000

        while self.status == Timer.TIMER_STATUS_ON:
            value = time.time() % 1000
            if value!= last:

                self.current_value += 1
                if self.tick_callback:
                    if self.mode == Timer.TIMER_MODE_TIMER:
                        self.tick_callback(self.to_time(self.timer_value - self.current_value))
                    elif self.mode == Timer.TIMER_MODE_STOPWATCH:
                        self.tick_callback(self.to_time(self.current_value))

                if self.mode == Timer.TIMER_MODE_TIMER and self.timer_value <= self.current_value:
                    if self.done_callback:
                        self.done_callback()
                    self.status = Timer.TIMER_STATUS_IDLE
                last = value

            await asyncio.sleep_ms(100)

    def deinit(self):
        self.status = Timer.TIMER_STATUS_IDLE
        if self._tick_task is not None:
            self._tick_task.cancel()

    def set_timer_value(self, hours=None, minutes=None, seconds=None):
        if self.is_idle():
            (h, m, s) = self.to_time(self.timer_value)
            self.timer_value = self.to_int(
                hours=hours if hours else h,
                minutes=minutes if minutes else m,
                seconds=seconds if seconds else s
            )
            return True

    def add_timer_value(self, hours=None, minutes=None, seconds=None):
        if self.is_idle():
            self.timer_value += ( \
                        (3_600 * hours if hours else 0)
                        + (60 * minutes if minutes else 0)
                        + (seconds if seconds else 0))
            # 360000 = 100 hours
            if self.timer_value < 0:
                self.timer_value = 360000 + self.timer_value
            self.timer_value  %= 360000

    def get_timer_value(self) -> (int, int, int):
        return self.to_time(self.timer_value)

    def get_current_value(self) -> (int, int, int):
        return self.to_time(self.current_value)

    def add_timer_value_by_context(self, value):
        if self.is_idle():
            if self.setup_context == Timer.TIMER_SET_CONTEXT_HOUR:
                self.add_timer_value(hours=value)
            elif self.setup_context == Timer.TIMER_SET_CONTEXT_MIN:
                self.add_timer_value(minutes=value)
            elif self.setup_context == Timer.TIMER_SET_CONTEXT_SEC:
                self.add_timer_value(seconds=value)
            return True

    def reset_timer_value(self):
        if self.is_idle():
            if self.mode == Timer.TIMER_MODE_STOPWATCH:
                self.current_value = 0
            else:
                self.timer_value = 0
            return True

    def set_setup_context(self, context: str):
        if context not in Timer.TIMER_SET_CONTEXT:
            raise ValueError(f"Unknown set context value: {context}")
        self.setup_context = context
        return True

    def set_mode(self, mode: str = None):
        if self.is_idle():
            if mode is None:
                mode =Timer.TIMER_MODE.next(self.mode)
            if mode not in Timer.TIMER_MODE:
                raise ValueError(f"Unknown mode value: {mode}")
            self.mode = mode
            self.current_value = 0
            return True

    def start(self):
        if self.is_idle():
            if self.mode == Timer.TIMER_MODE_STOPWATCH or (self.mode == Timer.TIMER_MODE_TIMER and self.timer_value > 0):
                if self.mode == Timer.TIMER_MODE_TIMER:
                    self.current_value = 0
                self.status = Timer.TIMER_STATUS_ON
                self._tick_task = asyncio.create_task(self._tick())
                return True

    def stop(self):
        if not self.is_idle():
            self.status = Timer.TIMER_STATUS_IDLE
            self._tick_task.cancel()
            return True

    def is_idle(self):
        return self.status == Timer.TIMER_STATUS_IDLE

    @staticmethod
    def to_time(value):
        hours = value // 3_600
        minutes = (value - (3_600 * hours)) // 60
        seconds = (value - 3_600 * hours) - 60 * minutes
        result = (hours, minutes, seconds)
        return result

    @staticmethod
    def to_int(hours, minutes, seconds):
        return 3_600 * hours + 60 * minutes + seconds
