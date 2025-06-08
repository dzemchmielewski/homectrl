import asyncio
import logging

import gc
from micropython import const

from analog_multiplexer import AnalogMultiplexer
from board.board_application import BoardApplication
from desk_fw.display_manager import DeskDisplayManager, OledDisplay_1_32
from rotary import RotaryIRQ

logging.basicConfig(level=logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

INA_ADDRESS = const(0x40)
INA_ORDER = [0, 1, 2, 3]

CHANNEL = const('channel')
REFRESH = const('refresh')
CHANNEL_INDEX = const('index')
CHANNEL_VOLTAGE = const('voltage')
CHANNEL_CURRENT = const('current')
CHANNEL_THRESHOLD = const('threshold')
CHANNEL_STATUS = const('status')
CHANNEL_MARK = const('mark')
CHANNEL_MARK_UP = const('up')
CHANNEL_MARK_DOWN = const('down')
CHANNEL_MARK_EMPTY = const('')

CHANNEL_STATUS_ERR = const("ERR")
CHANNEL_STATUS_ON = const("ON")
CHANNEL_STATUS_OFF = const("OFF")
CHANNEL_STATUS_ALERT = const("ALERT")
CHANNEL_STATUS_WARN = const("WARN")

SHOW_CHANNEL = const('show_channel')
ACTION_TIME = const('action_time')
BLANK_MODE = const('blank_mode')

BLANK_INACTIVITY_TIME = const(5 * 60 * 1_000)

class Testing(BoardApplication):

    def __init__(self):
        BoardApplication.__init__(self, 'desk')
        self._work_tasks = []

        self.channels = [{
            CHANNEL_INDEX: idx,
            CHANNEL_VOLTAGE: None,
            CHANNEL_CURRENT: None,
            CHANNEL_STATUS: None,
            CHANNEL_THRESHOLD: 2.0,
            CHANNEL_MARK: CHANNEL_MARK_EMPTY
        } for idx in range(12)]

        self.screen = {
            CHANNEL: None,
            CHANNEL_STATUS: None,
            CHANNEL_VOLTAGE: None,
            CHANNEL_CURRENT: None,
            REFRESH: None
        }

        self.data = {
            'name': self.name,
            ACTION_TIME: None,
            SHOW_CHANNEL: None,
            BLANK_MODE: False,
            'screen': self.screen,
            'led': {
                CHANNEL: None
            },
            'channels': self.channels
        }

        self.log = logging.getLogger('DESK')

        gc.collect()

        self.rotary = RotaryIRQ(pin_num_clk=39, pin_num_dt=38,
                        min_val=0, max_val=11, reverse=False, range_mode=RotaryIRQ.RANGE_WRAP)
        self.rotary.add_listener(self.on_change_rotary_encoder)

        gc.collect()

        self.manager = DeskDisplayManager()
        self.display = OledDisplay_1_32(1, 2, 1, 42, 41, 40, self.manager)
        # from machine import SPI
        # from machine import Pin
        #
        # gc.collect()
        #
        # self.spi = SPI(1, sck=Pin(2), mosi=Pin(1))
        #
        # gc.collect()
        #
        # dc, res, cs = Pin(41), Pin(40), Pin(42)
        # dc.init(dc.OUT, value=0)
        # res.init(res.OUT, value=1)
        # cs.init(cs.OUT, value=1)

        gc.collect()

        self.sensor_mplex = AnalogMultiplexer([14, 13, 47, 48][::-1], signal_pin=21, channels_range=12)
        self.led_mplex = AnalogMultiplexer([0, 35, 36, 37][::-1], enable_pin=45, channels_range=12)

        self.log.debug("initialized")

    def on_change_rotary_encoder(self):
        self.led_mplex.turn_off()
        self.led_mplex.set_channel(self.rotary.value())
        self.led_mplex.turn_on()

    async def read_touch(self):
        while True:
            touch = self.sensor_mplex.read_on()
            if len(touch) > 0:
                self.log.debug(f"TOUCH: {touch}")
                self.led_mplex.turn_off()
                self.led_mplex.set_channel(touch[0])
                self.led_mplex.turn_on()
            await asyncio.sleep_ms(250)


    async def start(self):
        await super().start()
        self.log.debug("start")
        self.led_mplex.set_channel(0)
        self.led_mplex.turn_on()
        self._work_tasks = [
            asyncio.create_task(self.read_touch())]

    def deinit(self):
        self.log.debug("deinit")
        for task in self._work_tasks:
            task.cancel()
        self.led_mplex.turn_off()



