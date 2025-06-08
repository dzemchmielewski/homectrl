import time
import asyncio
import json
import logging

from micropython import const
from machine import Pin, SoftI2C

from board.board_application import BoardApplication
from board.board_shared import Utils as util
from desk_fw.display_manager import DeskDisplayManager, OledDisplay_1_32
from toolbox.pinio import PinIO
from configuration import Configuration
import ina3221
from analog_multiplexer import AnalogMultiplexer
from rotary import RotaryIRQ
from pushbutton import Pushbutton

logging.basicConfig(level=logging.INFO)
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

BLANK_INACTIVITY_TIME = const(5 * 60 * 1_000)


class DeskApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'desk')
        self._work_tasks = []
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.channels = [{
            CHANNEL_INDEX: idx,
            CHANNEL_VOLTAGE: None,
            CHANNEL_CURRENT: None,
            CHANNEL_STATUS: None,
            CHANNEL_THRESHOLD: 1.0,
            CHANNEL_MARK: CHANNEL_MARK_EMPTY
        } for idx in range(12)]

        self.screen = {
            CHANNEL: None,
            CHANNEL_STATUS: None,
            CHANNEL_VOLTAGE: None,
            CHANNEL_CURRENT: None,
            REFRESH: None
        }

        self.alerts = []

        self.action_time = None
        self.current_channel = None
        self.blank_mode = False


        for i in [0, 4, 5]:
            self.channels[i][CHANNEL_MARK] = CHANNEL_MARK_UP
        for i in [1,2,3]:
            self.channels[i][CHANNEL_MARK] = CHANNEL_MARK_DOWN
        # self.channels[10][CHANNEL_THRESHOLD] = 0.6

        # self.green_led = PinIO(43)
        # self.blue_led = PinIO(44)

        self.relays = [PinIO(idx, False) for idx in [5, 7, 16, 18, 3, 9, 6, 15, 17, 8, 46, 10]]

        # Rotary encoder: A: 38, B:  39, C:  4
        self.rotary = RotaryIRQ(pin_num_clk=39, pin_num_dt=38,
                                   min_val=0, max_val=11, reverse=False, range_mode=RotaryIRQ.RANGE_WRAP)
        self.rotary.add_listener(self.on_change_rotary_encoder)

        self.rotary_button = Pushbutton(Pin(4, Pin.IN), suppress=True)
        self.rotary_button.press_func(self.on_push_rotary_button)

        self.manager = DeskDisplayManager()
        self.display = OledDisplay_1_32(1, 2, 1, 42, 41, 40, self.manager)

        # WARNING!
        # I don't know why, but AnalogMultiplexer initialization has to be
        # AFTER the OLED initialization.
        self.led_mplex = AnalogMultiplexer([0, 35, 36, 37][::-1], enable_pin=45, channels_range=12)
        self.sensor_mplex = AnalogMultiplexer([14, 13, 47, 48][::-1], signal_pin=21, channels_range=12)

        bus = SoftI2C(scl=Pin(11), sda=Pin(12), freq=400000)
        self.ina = [ina3221.INA3221(bus, i2c_addr=INA_ADDRESS + i) for i in INA_ORDER]
        for idx, ina in enumerate(self.ina):
            try:
                ina.update(reg=ina3221.C_REG_CONFIG,
                           mask=ina3221.C_AVERAGING_MASK | ina3221.C_VBUS_CONV_TIME_MASK | ina3221.C_SHUNT_CONV_TIME_MASK | ina3221.C_MODE_MASK,
                           value=ina3221.C_AVERAGING_128_SAMPLES | ina3221.C_VBUS_CONV_TIME_8MS | ina3221.C_SHUNT_CONV_TIME_8MS | ina3221.C_MODE_SHUNT_AND_BUS_CONTINOUS)

                for c in range(3):
                    ina.enable_channel(c + 1)
                    self.channels[3 * idx + c][CHANNEL_STATUS] = CHANNEL_STATUS_OFF

                while not ina.is_ready:
                    self.log.info(f"Waiting for INA #{idx} ({hex(ina.i2c_addr)})...")
                    time.sleep_ms(50)

                self.log.info(f"INA #{idx} ({hex(ina.i2c_addr)}) is ready")

            except Exception as e:
                self.log.error(f"INA #{idx} ({hex(ina.i2c_addr)}) initialization failed: {e}")
                for c in range(3):
                    self.channels[3 * idx + c][CHANNEL_STATUS] = CHANNEL_STATUS_ERR

        #Initial value:
        self.set_display_channel(9)


    def read(self, to_json = True):
        result = {
            "action_time": self.action_time,
            "current_channel": self.current_channel,
            "blank_mode": self.blank_mode
        }
        return json.dumps(result) if to_json else result

    def relay_channel(self, channel: int, status: str):
        self.channels[channel][CHANNEL_STATUS] = status
        if status == CHANNEL_STATUS_ON:
            self.relays[channel].on()
        else:
            self.relays[channel].off()
        self.action_time = time.ticks_ms()

    def on(self, channel: int):
        self.relay_channel(channel, CHANNEL_STATUS_ON)

    def off(self, channel: int):
        self.relay_channel(channel, CHANNEL_STATUS_OFF)

    def set_display_channel(self, channel_number):
        if channel_number != self.current_channel:
            self.rotary._value = channel_number
            self.current_channel = channel_number
            self.led_mplex.turn_off()
            self.led_mplex.set_channel(channel_number)
            self.led_mplex.turn_on()
            self.action_time = time.ticks_ms()
            self.refresh_screen()

    def refresh_screen(self):
        show_channel = self.current_channel
        self.screen["channel"] = show_channel
        self.screen[CHANNEL_STATUS] = self.channels[show_channel][CHANNEL_STATUS]
        self.screen[CHANNEL_VOLTAGE] = self.channels[show_channel][CHANNEL_VOLTAGE]
        self.screen[CHANNEL_CURRENT] = self.channels[show_channel][CHANNEL_CURRENT]
        self.screen[CHANNEL_MARK] = self.channels[show_channel][CHANNEL_MARK]
        self.screen['invert'] = self.screen[CHANNEL_STATUS] not in [CHANNEL_STATUS_ON, CHANNEL_STATUS_OFF]
        self.manager.refresh(self.screen)
        self.turn_display(True)
        self.display.show()
        self.screen[REFRESH] = util.time_str()

    def turn_display(self, turn: bool):
        # Turn on/off display and led:
        if turn and self.blank_mode:
            self.blank_mode = False
            self.led_mplex.turn_on()
            self.display.poweron()
        elif not turn and not self.blank_mode:
            self.blank_mode = True
            self.led_mplex.turn_off()
            self.display.poweroff()

    async def read_touch(self):
        while not self.exit:
            touch = self.sensor_mplex.read_on()
            if len(touch) > 0:
                channel = touch[0]
                self.set_display_channel(channel)
            await asyncio.sleep_ms(100)

    def on_change_rotary_encoder(self):
        self.set_display_channel(self.rotary.value())

    def on_push_rotary_button(self):
        current_channel = self.current_channel
        if self.channels[current_channel][CHANNEL_STATUS] == CHANNEL_STATUS_ON:
            self.off(current_channel)
        else:
            self.on(current_channel)

    async def read_ina(self):
        while not self.exit:
            for idx, ina in enumerate(self.ina):
                # while not ina.is_ready():
                #     await asyncio.sleep_ms(50)
                try:
                    for c in range(3):
                        ch = 3 * idx + (2-c)
                        # Do not check this condition - all channels should be enabled
                        # if ina.is_channel_enabled(c + 1):
                        channel = self.channels[ch]
                        #if channel[CHANNEL_STATUS] != CHANNEL_STATUS_ERR:
                        channel[CHANNEL_VOLTAGE] = ina.bus_voltage(c + 1) + ina.shunt_voltage(c + 1)
                        channel[CHANNEL_CURRENT] = abs(ina.current(c + 1))

                        # Check if the current exceeds the threshold:
                        if channel[CHANNEL_CURRENT] > channel[CHANNEL_THRESHOLD]:
                            if channel[CHANNEL_STATUS] != CHANNEL_STATUS_ALERT:
                                self.relay_channel(ch, CHANNEL_STATUS_ALERT)
                                self.alerts.append({
                                    'channel': ch,
                                    'current': channel[CHANNEL_CURRENT],
                                    'threshold': channel[CHANNEL_THRESHOLD],
                                    'datetime': util.time_str()
                                })

                except Exception as e:
                    self.log.error(f"Read INA exception: {e}")
                    for c in range(3):
                        self.channels[3 * idx + (2-c)][CHANNEL_STATUS] = CHANNEL_STATUS_ERR
                        self.channels[3 * idx + (2-c)][CHANNEL_VOLTAGE] = -1
                        self.channels[3 * idx + (2-c)][CHANNEL_CURRENT] = -1
                        # TODO: handle exception

            if (self.channels[self.current_channel][CHANNEL_STATUS] != self.screen[CHANNEL_STATUS]
                or self.channels[self.current_channel][CHANNEL_VOLTAGE] != self.screen[CHANNEL_VOLTAGE]
                or self.channels[self.current_channel][CHANNEL_CURRENT] != self.screen[CHANNEL_CURRENT]):
                if not self.blank_mode:
                    self.refresh_screen()

            await asyncio.sleep_ms(300)

    async def dim_mode(self):
        while not self.exit:
            if self.action_time and time.ticks_ms() - self.action_time > BLANK_INACTIVITY_TIME:
                # Turn off display and led after some time of inactivity:
                self.turn_display(False)
            await asyncio.sleep_ms(1_000)

    async def start(self):
        await super().start()

        self._work_tasks = [
            asyncio.create_task(self.read_touch()),
            asyncio.create_task(self.read_ina()),
            asyncio.create_task(self.dim_mode())
        ]

    def deinit(self):
        super().deinit()

        for task in self._work_tasks:
            task.cancel()

        self.display.poweroff()
        self.led_mplex.turn_off()
        for p in self.relays:
            p.off()
