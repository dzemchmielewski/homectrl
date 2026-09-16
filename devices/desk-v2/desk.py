import asyncio
import json
import logging
from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin, SoftI2C
from ina226 import INA226


logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

R_SHUNT_OHMS = 0.01
MAX_EXPECTED_AMPS = 5
# CURRENT_ALERT_MA = 1_200
CURRENT_ALERT_MA = [
    2, # 3.3V
    2, # 5V
    2, # 12V
]


class DeskApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'desk')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)
        i2c = SoftI2C(scl=Pin(4), sda=Pin(3), freq=400_000)

        self.ina = [
            INA226(i2c, addr=0x44 + 0), # 3.3V
            INA226(i2c, addr=0x44 + 2), # 5V
            INA226(i2c, addr=0x44 + 1), # 12V
        ]
        for i in range(3):
            self.ina[i].calibrate(
                r_shunt_ohms=R_SHUNT_OHMS,
                max_expected_amps=MAX_EXPECTED_AMPS)
            self.ina[i].configure(
                avg=INA226.AVG_16,
                vbusct=INA226.VBUSCT_588US,
                vshct=INA226.VSHCT_588US,
                mode=INA226.MODE_SHUNT_BUS_CONTINUOUS)
            self.ina[i].set_alert(INA226.ALERT_SHUNT_OVER,
                                  limit_volts=(CURRENT_ALERT_MA[i] / 1000.0) * R_SHUNT_OHMS,
                                  latch=True)

        self._relay = [
            Pin(5, Pin.OUT), # 3.3V
            Pin(6, Pin.OUT), # 5V
            Pin(7, Pin.OUT), # 12V
        ]

        # ALERTS:
        # GPIO 2 12V
        # GPIO 1 5V
        # GPIO 0 3.3V

        self.alerts = [asyncio.ThreadSafeFlag()] * 3
        self.tasks = None

        for channel in range(3):
            pin = Pin(channel, Pin.IN, Pin.PULL_UP)
            if pin.value() == 0:
                # A stale latch from a previous run/power-up condition - clear it so we
                # start from a known state instead of waiting for a fresh falling edge.
                self.ina[channel].read_alert_flags()
            pin.irq(trigger=Pin.IRQ_FALLING, handler=lambda p: self.alerts[channel].set())


    def read(self, to_json = True):
        result = {
            "current_mA": [self.ina[i].current_mA for i in range(3)]
        }
        return json.dumps(result) if to_json else result

    def relay(self, value=1, channel=None):
        if channel is not None:
            self._relay[channel % 3].value(value)
        else:
            [self._relay[i].value(value) for i in range(3)]

    async def alert_task(self, channel):
        while True:
            await self.alerts[channel].wait()
            print()
            aff, cvrf, ovf = self.ina[channel].read_alert_flags()  # reading clears AFF, releases the pin
            if aff:
                self.relay(channel=channel)
                print(">>> ALERT(#{:d}): current = {:.2f} mA (limit {} mA) <<<".format(
                    channel, self.ina[channel].current_mA, CURRENT_ALERT_MA[channel]))
            elif ovf:
                print(">>> ALERT: math overflow flag set - reading out of range <<<")
            # Small debounce: if the current is still over threshold the
            # comparator re-latches (and re-fires the IRQ) on the next
            # conversion, so this just keeps the console readable.
            await asyncio.sleep_ms(200)

    async def start(self):
        await super().start()
        self.tasks = [asyncio.create_task(self.alert_task(channel)) for channel in range(3)]

    def deinit(self):
        super().deinit()
        [task.cancel() for task in self.tasks]
