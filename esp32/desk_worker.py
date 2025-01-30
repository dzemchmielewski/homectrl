import json
import time

from machine import Pin, SoftI2C

from board.command_parser import CommandParser
from common.common import time_ms

from board.worker import MQTTWorker
from desk.display_manager import DeskDisplayManager, OledDisplay_1_32
from desk.rotary import ReadOnceRotary

from modules.analog_multiplexer import AnalogMultiplexer
from modules.button import SimpleButton
from modules.ina3221 import *
from modules.pinio import PinIO

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

class DeskWorker(MQTTWorker):

    def __init__(self, debug=False):
        super().__init__("desk", debug)

        worker_data = self.get_data()
        worker_data.guard = -1
        worker_data.loop_sleep = 0.001
        worker_data.data = {
            "name": self.name,
            "process": None,
            ACTION_TIME: None,
            SHOW_CHANNEL: 0,
            BLANK_MODE: False,
            'screen': {
                CHANNEL: None,
                CHANNEL_STATUS: None,
                CHANNEL_VOLTAGE: None,
                CHANNEL_CURRENT: None,
                REFRESH: None
            },
            'led': {
                CHANNEL: None
            },

            'channels': [{
                CHANNEL_INDEX: idx,
                CHANNEL_VOLTAGE: None,
                CHANNEL_CURRENT: None,
                CHANNEL_STATUS: None,
                CHANNEL_THRESHOLD: 2.0,
                CHANNEL_MARK: CHANNEL_MARK_EMPTY
            } for idx in range(12)]
        }

        channels = worker_data.data["channels"]
        for i in [0, 4, 5]:
            channels[i][CHANNEL_MARK] = CHANNEL_MARK_UP
        for i in [1,2,3]:
            channels[i][CHANNEL_MARK] = CHANNEL_MARK_DOWN
        channels[0][CHANNEL_THRESHOLD] = 0.17

        self.cp = CommandParser({
            "help": None,
            "channel": {
                "on": int,
                "off": int,
                "show": int}})
        self.help = f"{list(self.cp.commands.keys())}"

        self.green_led = PinIO(43)
        self.blue_led = PinIO(44)

        # [10, 46, 8, 17, 15, 6, 9, 3, 18, 16, 7, 5]
        self.relays = [PinIO(idx, False) for idx in [5, 7, 16, 18, 3, 9, 6, 15, 17, 8, 46, 10]]

        self.led_mplex = AnalogMultiplexer([0, 35, 36, 37][::-1], enable_pin=45, channels_range=12)
        self.sensor_mplex = AnalogMultiplexer([14, 13, 47, 48][::-1], signal_pin=21, channels_range=12)

        # Rotary encoder: A: 38, B:  39, C:  4
        self.rotary = ReadOnceRotary(pin_num_clk=39, pin_num_dt=38,
                                min_val=0, max_val=11, reverse=False, range_mode=ReadOnceRotary.RANGE_WRAP)
        self.rotary_button = SimpleButton(4)

        self.manager = DeskDisplayManager()
        self.screen = OledDisplay_1_32(1, 2, 1, 42, 41, 40, self.manager)
        self.screen.show()

        bus = SoftI2C(scl=Pin(11), sda=Pin(12), freq=400000)
        self.ina = [INA3221(bus, i2c_addr=INA_ADDRESS + i) for i in INA_ORDER]
        for idx, ina in enumerate(self.ina):
            try:
                ina.update(reg=C_REG_CONFIG,
                           mask=C_AVERAGING_MASK | C_VBUS_CONV_TIME_MASK | C_SHUNT_CONV_TIME_MASK | C_MODE_MASK,
                           value=C_AVERAGING_128_SAMPLES | C_VBUS_CONV_TIME_8MS | C_SHUNT_CONV_TIME_8MS | C_MODE_SHUNT_AND_BUS_CONTINOUS)

                for c in range(3):
                    ina.enable_channel(c + 1)
                    worker_data.data['channels'][3 * idx + c][CHANNEL_STATUS] = CHANNEL_STATUS_OFF

                while not ina.is_ready:
                    print(".", end='')
                    time.sleep(0.05)

                print(f"INA #{idx} ({hex(ina.i2c_addr)}) is ready")

            except Exception as e:
                for c in range(3):
                    worker_data.data['channels'][3 * idx + c][CHANNEL_STATUS] = CHANNEL_STATUS_ERR
                self.handle_exception(e, False)

    def handle_help(self):
        return f"DESK COMMANDS: {self.help}"

    def handle_message(self, msg):
        command = self.cp.parse(msg)
        if (c := command['command']) is None:
            return f'{{"error": "{command["error"]}"}}'
        params = command["params"]
        data = self.get_data().data

        if c == "help":
            return f'{{"message": "Available commands: {self.help}"}}'
        elif c.startswith("channel"):
            if params < 0 or params >= len(data['channels']):
                return f'{{"error": "channel number nust be between 0 and {len(data['channels']) - 1}"}}'
            if c == "channel show":
                data[SHOW_CHANNEL] = params
                return json.dumps(data['channels'][params])
            elif c == "channel on":
                data['channels'][params][CHANNEL_STATUS] = CHANNEL_STATUS_ON
                return json.dumps(data['channels'][params])
            elif c == "channel off":
                data['channels'][params][CHANNEL_STATUS] = CHANNEL_STATUS_OFF
                return json.dumps(data['channels'][params])

        return f'{{"error": "Unexpected error. Something is not implemented. Command: {command}"}}'

    def start(self):
        self.begin()
        worker_data = self.get_data()
        screen = worker_data.data['screen']
        led = worker_data.data['led']
        channels = worker_data.data['channels']
        print(f"START: {channels}")

        with open("/desk_init.txt", 'w') as f:
            f.write(self.the_time_str() + '\n')

        while self.keep_working():
            try:
                publish = False

                # Read INA values:
                for idx, ina in enumerate(self.ina):
                    try:
                        for c in range(3):
                            # Do not check this condition - all channels should be enabled
                            # if ina.is_channel_enabled(c + 1):
                            channel = channels[3 * idx + (2-c)]
                            if channel[CHANNEL_STATUS] != CHANNEL_STATUS_ERR:
                                channel[CHANNEL_VOLTAGE] = ina.bus_voltage(c + 1) + ina.shunt_voltage(c + 1)
                                channel[CHANNEL_CURRENT] = abs(ina.current(c + 1))
                            else:
                                # TODO: display manager should accept None
                                channel[CHANNEL_VOLTAGE] = -1
                                channel[CHANNEL_CURRENT] = -1
                    except Exception as e:
                        for c in range(3):
                            channels[3 * idx + (2-c)][CHANNEL_STATUS] = CHANNEL_STATUS_ERR
                            channels[3 * idx + (2-c)][CHANNEL_VOLTAGE] = -1
                            channels[3 * idx + (2-c)][CHANNEL_CURRENT] = -1
                            self.handle_exception(e, False)


                # Read touch buttons and change the display channel:
                touch = self.sensor_mplex.read_on()
                if len(touch) > 0:
                    worker_data.data[SHOW_CHANNEL] = touch[0]
                    worker_data.data[ACTION_TIME] = time_ms()


                # Read value from rotary encoder and change the display channel:
                if (rotary_value := self.rotary.value()) is not None:
                    worker_data.data[SHOW_CHANNEL] = rotary_value
                    worker_data.data[ACTION_TIME] = time_ms()

                # Turn on led for selected channel:
                show_channel = worker_data.data[SHOW_CHANNEL]

                if show_channel != led['channel']:
                    led['channel'] = show_channel
                    self.led_mplex.set_channel(show_channel)
                    self.led_mplex.turn_on()
                    worker_data.data[ACTION_TIME] = time_ms()

                # Adjust rotary encoder value:
                self.rotary._value = show_channel

                # Read rotary button - change the currently selected
                # channel relay value if button is clicked:
                if self.rotary_button.clicked():
                    if channels[show_channel][CHANNEL_STATUS] == CHANNEL_STATUS_ON:
                        channels[show_channel][CHANNEL_STATUS] = CHANNEL_STATUS_OFF
                    else:
                        channels[show_channel][CHANNEL_STATUS] = CHANNEL_STATUS_ON
                    worker_data.data[ACTION_TIME] = time_ms()

                for idx, channel in enumerate(channels):
                    # Check if the current exceeds the threshold:
                    if channel[CHANNEL_CURRENT] > channel[CHANNEL_THRESHOLD]:
                        channel[CHANNEL_STATUS] = CHANNEL_STATUS_ALERT

                    # Set relays according to the current channel state:
                    if channel[CHANNEL_STATUS] == CHANNEL_STATUS_ON:
                        self.relays[idx].on()
                    else:
                        self.relays[idx].off()

                if worker_data.data[ACTION_TIME] and time_ms() - worker_data.data[ACTION_TIME] > BLANK_INACTIVITY_TIME:
                    # Turn off display and led after some time of inactivity:
                    if not worker_data.data[BLANK_MODE]:
                        worker_data.data[BLANK_MODE] = True
                        self.led_mplex.turn_off()
                        self.screen.poweroff()
                else:
                    # Turn on display and led:
                    if worker_data.data[BLANK_MODE]:
                        worker_data.data[BLANK_MODE] = False
                        self.led_mplex.turn_on()
                        self.screen.poweron()

                    # Display channel values:
                    if (show_channel != screen["channel"]
                            or channels[show_channel][CHANNEL_STATUS] != screen[CHANNEL_STATUS]
                            or channels[show_channel][CHANNEL_VOLTAGE] != screen[CHANNEL_VOLTAGE]
                            or channels[show_channel][CHANNEL_CURRENT] != screen[CHANNEL_CURRENT]):
                        screen["channel"] = show_channel
                        screen[CHANNEL_STATUS] = channels[show_channel][CHANNEL_STATUS]
                        screen[CHANNEL_VOLTAGE] = channels[show_channel][CHANNEL_VOLTAGE]
                        screen[CHANNEL_CURRENT] = channels[show_channel][CHANNEL_CURRENT]
                        screen[CHANNEL_MARK] = channels[show_channel][CHANNEL_MARK]
                        screen['invert'] = screen[CHANNEL_STATUS] not in [CHANNEL_STATUS_ON, CHANNEL_STATUS_OFF]
                        self.manager.refresh(screen)
                        self.screen.show()
                        screen[REFRESH] = time_ms()


                # Save last process readable time
                worker_data.data['process'] = self.the_time_str()

                if publish:
                    self.mqtt_publish()
                else:
                    self.mqtt_ping()
            except BaseException as e:
                self.handle_exception(e)

        self.screen.poweroff()
        self.led_mplex.turn_off()
        for p in self.relays:
            p.off()
        self.end()

# # Test display:
# from desk.display_manager import DeskDisplayManager, OledDisplay_1_32
# manager = DeskDisplayManager()
# screen = OledDisplay_1_32(1, 2, 1, 42, 41, 40, manager)
# d = {"channel": 5, "values": [32.975, 7.889]}
# ba = manager.refresh(d)
# screen.show()
