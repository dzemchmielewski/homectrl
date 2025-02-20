import asyncio
import json

from machine import Pin, SoftI2C, SPI

import config
import time
from configuration import Configuration

import board.board_shared as shared
from board.board_application import BoardApplication

from ft6x36 import FT6x36
import st7789
from display_manager import DisplayManager
from max6675 import MAX6675, NoThermocoupleAttached
from buzz_player import BuzzPlayer
from timer import Timer


class Touch(shared.EventEmitter, shared.EventConsumer):

    LONG_TAP_MS =  800

    def __init__(self, touch:  FT6x36):
        shared.EventEmitter.__init__(self, 'touch')
        shared.EventConsumer.__init__(self, 'touch')
        self.touch = touch
        self._read_task = asyncio.create_task(self._read_touch())
        self.one_time_callback = []

    async def consume(self, event: dict):
        self.one_time_callback.append(event)
        return True

    def do_emit(self, type: str, time: int, point: []):
        self.emit({
            'recipient': 'display',
            'type': type,
            'time': time,
            'point': point})

    def tap_handler(self, type: str, time: int, point: []):
        if len(self.one_time_callback) > 0:
            for data in self.one_time_callback:
                data['callback']({'type': type,
                                  'time': time,
                                  'point': point})
            self.one_time_callback = []
        else:
            self.do_emit(type, time, point)

    def get_positions(self):
        p = self.touch.get_positions()
        if len(p) > 1 and p[1] == (0xFFF, 0xFFF, 0xFF, 0xF):
            self.log.warning(f"Caught false tap: {p}")
            return []
        return p

    async def _read_touch(self):
        position = None
        start_ms = 0
        long_start_ms = 0

        while not self.exit:
            p = self.get_positions()
            if position:
                if len(p) > 0:
                    if position != p:
                        position = p
                        self.tap_handler('tap-move', time.ticks_ms() - start_ms, p)
                    else:
                        if time.ticks_ms() - long_start_ms > self.LONG_TAP_MS:
                            self.tap_handler('tap-keep', time.ticks_ms() - long_start_ms, p)
                            long_start_ms = time.ticks_ms()
                else:
                    self.tap_handler('tap-out', time.ticks_ms() - start_ms, position)
                    position = None
                    start_ms = 0
                    long_start_ms = 0

            else:
                if len(p) > 0:
                    position = p
                    start_ms = time.ticks_ms()
                    long_start_ms = start_ms
                    self.tap_handler('tap-in', 0, p)

            await asyncio.sleep_ms(30)

    def deinit(self):
        super().deinit()
        self._read_task.cancel()


class Thermometer(shared.Exitable, shared.EventEmitter):
    def __init__(self, thermometer: MAX6675):
        shared.Exitable.__init__(self)
        shared.EventEmitter.__init__(self, 'thermometer')
        self._therm_task = asyncio.create_task(self._read())
        self.thermometer = thermometer
        self.temperature = None

    async def _read(self):
        while not self.exit:
            try:
                value = self.thermometer.read()
            except NoThermocoupleAttached:
                value = None
            if value != self.temperature:
                self.emit({
                    'recipient': 'display',
                    'part-recipient': 'dis-temp',
                    'value': value
                })
                self.emit({
                    'recipient': 'owen',
                    'data': {
                        'transient_temperature': value
                    }
                })
                self.temperature = value
            await asyncio.sleep_ms(1_000)

    def deinit(self):
        super().deinit()
        self._therm_task.cancel()


class Alarm(shared.EventConsumer, shared.EventEmitter):
    def __init__(self, buzz_player: BuzzPlayer):
        shared.EventConsumer.__init__(self, 'alarm')
        shared.EventEmitter.__init__(self, 'alarm')
        self._alarm_timeout_task = asyncio.create_task(self._alarm_timeout())
        self.buzz_player = buzz_player
        self.alarm_ms = None

    async def consume(self, event: dict):
        self.start() if event['alarm'] else self.stop()

    def wait_for_touch(self, data):
        if self.alarm_ms:
            self.stop()

    def start(self):
        self.log.info("ALARM start")
        self.buzz_player.start()
        self.alarm_ms = time.ticks_ms()
        self.emit({
            'recipient': 'touch',
            'callback': self.wait_for_touch
        })
        self.emit({
            'recipient': 'display',
            'allow_dim': False
        })

    def stop(self):
        self.log.info("ALARM stop")
        self.buzz_player.stop()
        self.alarm_ms = None
        self.emit({
            'recipient': 'display',
            'allow_dim': True
        })

    async def _alarm_timeout(self):
        while not self.exit:
            if self.alarm_ms is not None and time.ticks_ms() - self.alarm_ms > config.ALARM_TIMEOUT * 1_000:
                self.stop()
            await asyncio.sleep_ms(1_000)

    def deinit(self):
        super().deinit()
        self._alarm_timeout_task.cancel()
        self.buzz_player.deinit()


class TimerManager(shared.EventEmitter, shared.EventConsumer):

    def __init__(self):
        shared.EventEmitter.__init__(self, 'timer')
        shared.EventConsumer.__init__(self, 'timer')
        self.timer = Timer(tick_callback=self.value_to_display, done_callback=self._on_done)
        self.timer_display = None

    def deinit(self):
        super().deinit()
        self.timer.deinit()

    def initial(self):
        self.to_display({
            'part-recipient': 'btn-start',
            'label': 'start'
        })
        self.to_display({
            'part-recipient': 'dis-set',
            'label': self.timer.setup_context
        })
        self.to_display({
            'part-recipient': 'btn-mode',
            'label': self.timer.mode
        })
        self.value_to_display(self.timer.get_timer_value())

    def _on_done(self):
        self.on_status_change('done')

    def value_to_display(self, value):
        self.to_display({
            'part-recipient': 'dis-timer',
            'value': value
        })
        self.timer_display = value

    def update_display(self):
        if self.timer.mode == Timer.TIMER_MODE_TIMER:
            self.value_to_display(self.timer.get_timer_value())
        else:
            self.value_to_display(self.timer.get_current_value())

    def to_display(self, data: dict):
        data['recipient'] = 'display'
        self.emit(data)

    def to_alarm(self, data: dict):
        data['recipient'] = 'alarm'
        self.emit(data)

    async def consume(self, event: dict):

        if event['sender'] == 'btn-mode':
            if self.timer.set_mode():
                self.to_display({
                    'part-recipient': 'btn-mode',
                    'label': self.timer.mode
                })
                self.update_display()

        elif  event['sender'] == 'btn-start':
            if event['type'] == 'click-keep':
                config.EXIT = True
            is_start = self.timer.is_idle()
            success = self.timer.start() if is_start else self.timer.stop()
            if success:
                self.on_status_change('start' if is_start else 'stop')

        elif  event['sender'] == 'btn-reset':
            if self.timer.reset_timer_value():
                self.update_display()

        elif event['sender'] in ('btn-hour', 'btn-min', 'btn-sec'):
            if self.timer.set_setup_context(event['sender'].split('-')[1]):
                self.to_display({
                    'part-recipient': 'dis-set',
                    'label': self.timer.setup_context
                })

        elif event['sender'] in ('btn-up', 'btn-down'):
            plus_minus = 1 if event['sender'] == 'btn-up' else -1
            if event['type'] == 'click-keep':
                val = 10
            elif event['type'] == 'click-short':
                val = 1
            elif event['type'] == 'click-long':
                # Do nothing. Long click was handled previously by click-keep
                val = 0
            else:
                raise Exception(f"Unknown type in the event data: {event}")
            if self.timer.add_timer_value_by_context(plus_minus * val):
                self.update_display()

    def on_status_change(self, status: str):
        self.log.info(f"TIMER {status}")
        if not status == 'start':
            self.update_display()

        self.to_display({
            'part-recipient': 'btn-start',
            'label': 'stop' if status == 'start' else 'start'
        })
        self.to_display({
            'part-recipient': 'dis-set',
            'label': 'empty' if status == 'start' else self.timer.setup_context
        })
        if status == 'done':
            self.to_alarm({
                'alarm': True
            })
        elif status == 'start':
            self.to_display({
                'allow_dim': False
            })
        elif status == 'stop':
            self.to_display({
                'allow_dim': True
            })


class OwenApplication(BoardApplication, shared.EventConsumer):
    def __init__(self):
        BoardApplication.__init__(self, 'owen')
        shared.EventConsumer.__init__(self, self.name)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

    def read(self, to_json = True):
        result = {
            "transient_temperature": self.therm.temperature,
            "is_dimmed": self.display.is_dimmed,
            "timer_display": self.timer.timer_display
        }
        return json.dumps(result) if to_json else result

    async def start(self):
        await super().start()

        self.touch = Touch(FT6x36(SoftI2C(scl=Pin(40), sda=Pin(42))))

        self.display = DisplayManager(st7789.ST7789(
            SPI(2, baudrate=40_000_000, sck=Pin(15), mosi=Pin(7), miso=Pin(39)),
            240,320,
            reset=Pin(5, Pin.OUT),
            cs=Pin(6, Pin.OUT),
            dc=Pin(4, Pin.OUT),
            backlight=Pin(16, Pin.OUT),
            rotation=0))

        self.therm =Thermometer(MAX6675(so_pin=11, cs_pin=12, sck_pin=13))

        self.timer = TimerManager()

        self.alarm = Alarm(BuzzPlayer(8, 'MahnaMahna', silent=config.SILENT_ALARM))

        self.display.listen_to(self.touch)
        self.display.listen_to(self.therm)
        self.display.listen_to(self.timer)
        self.display.listen_to(self.alarm)

        self.timer.listen_to(self.display)

        self.alarm.listen_to(self.timer)

        self.touch.listen_to(self.alarm)
        self.touch.listen_to(self.display)

        self.listen_to(self.timer)

        self.timer.timer.set_timer_value(*config.DEFAULT_TIMER_VALUE)
        self.timer.initial()

        self.listen_to(self.therm)
        self.log.info("Owen started")

    async def consume(self, event: dict):
        if (data := event.get('data')) is not None:
            await self.publish(self.topic_data, data, False)

#LCD:
# 6 CS
#  5 RESET
#  4 D/C
#  7 SDI (MOSI)
#  15 SCK
#  16 LED
#  39 SDO (MISO)

# CTP:
#  40 CLK/SCL
#  41 CS/RST
#  42 DIN/SDA
#  2 OUT
#  1 IRQ/INT
