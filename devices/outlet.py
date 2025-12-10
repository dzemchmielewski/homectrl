import asyncio
import json
import logging
import time

from SR74HC595 import SR74HC595, SR74HC595_Sync
from board.board_application import BoardApplication, Facility
from segment_lcd8 import SegmentLCD8
from toolbox.pinio import PinIO
from configuration import Configuration
from machine import Pin, SoftI2C
# from ac_voltage import ACVoltage
from veml7700 import LuxDarkness, VEML7700

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

class Relay(Facility):

    def on(self):
        self.value = 1
        self.endpoint.on()

    def off(self):
        self.value = 0
        self.endpoint.off()


class OutletApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'outlet', use_mqtt=True)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.lcd = Facility("lcd",
                            SegmentLCD8(SR74HC595_Sync(8*4, 7, 8, 9), segments=4))
        # self.energy = Facility("energy", ACVoltage(SoftI2C(scl=Pin(1), sda=Pin(2)), 3, 0), None)

        lux = LuxDarkness(
            VEML7700(address=0x10, it=100, gain=1/8, i2c=SoftI2C(scl=Pin(21), sda=Pin(0), freq=10000)),
            queue_size=10, threshold=100)
        self.lux = Facility("lux", lux, (None, None, None))

        self.switch = Facility("switch", PinIO(10, pull=Pin.PULL_DOWN), 0, register_access=False)
        self.touch = Facility("touch", PinIO(20, pull=Pin.PULL_DOWN), 0, register_access=False)
        self.relay = Relay("relay", PinIO(6), None, register_access=True)
        self.lcd.value = 'helo'

    def read(self, to_json = True):
        result = (self.lcd.to_dict()
                  #| self.energy.to_dict()
                  | self.lux.to_dict()
                  | self.switch.to_dict()
                  | self.relay.to_dict()
                  )
        return json.dumps(result) if to_json else result

    def mqttdata(self):
        return {
            'darkness': self.lux.value[0],
            'lux': self.lux.value[1],
            'relay': self.relay.value,
            'light': self.relay.value,
        }

    async def lcd_task(self):
        try:
            while not self.exit:
                if self.lcd.value:
                    if time.time_ms() - self.lcd.set > 5 * 1_000:
                        self.lcd.endpoint.clear()
                        self.lcd.value = None
                    else:
                        self.lcd.endpoint.set(self.lcd.value)
                await asyncio.sleep_ms(333)
        except Exception as e:
            self.log.error(f"LCD task error: {e}")


    # async def energy_task(self):
    #     while not self.exit:
    #         self.energy.value = (self.energy.endpoint.read() / 100) * 230
    #         await asyncio.sleep_ms(200)

    async def lux_task(self):
        while not self.exit:
            current_darkness, _, _ = self.lux.value
            reading = self.lux.endpoint.read()
            if current_darkness != reading[0]:
                self.log.info(f"Darkness changed: {self.lux.value}")
            self.lux.value = reading
            await asyncio.sleep(5)

    # async def lux_task(self):
    #     while not self.exit:
    #         # Read lux and publish every 5 minutes at xx:00, xx:05, xx:10, ...
    #         self.lux.value = self.lux.endpoint.read()
    #         self.log.info(f"Lux reading: {self.lux.value}")
    #         await self.publish(self.topic_data, {'lux': self.lux.value[1]}, True)
    #
    #         _, _, _, _, min, sec, _, _ = time.localtime()
    #         next_minute = ((min + 5) // 5) * 5
    #         seconds_to_next = ((next_minute - min) * 60 - sec) + 1
    #         self.log.info(f"Going sleep for {seconds_to_next} seconds.")
    #         await asyncio.sleep(seconds_to_next)

    async def switch_task(self):
        while not self.exit:
            value = self.switch.endpoint.get()
            if value != self.switch.value:
                self.log.info(f"Switch changed: {value}")
                self.switch.value = value
                if value == 1:
                    self.lcd.value = 'auto'
                else:
                    self.relay.off()
                    self.lcd.value = 'off'
            await asyncio.sleep_ms(333)

    async def relay_task(self):
        initial = True
        self.relay.off()
        while not self.exit:
            publish = False
            if self.switch.value == 1:  # switch is ON
                if self.relay.value == 0:  # relay is OFF

                    if self.lux.value[0]:  # is dark
                        self.log.info(f"Relay ON")
                        self.relay.on()
                        self.lcd.value = 'on'
                        publish = True

                else:  # relay is ON
                    if not self.lux.value[0]:  # is not dark
                        self.log.info(f"Relay OFF")
                        self.relay.off()
                        self.lcd.value = 'off'
                        publish = True

            elif self.switch.value == 0:  # switch is OFF
                value = self.relay.endpoint.get()
                if value != self.relay.value:
                    self.log.info(f"Relay changed: {value}")
                    self.relay.value = value
                    self.lcd.value = 'off' if value == 0 else 'on'
                    publish = True

            else:
                pass

            if publish or initial:
                initial = False
                await self.publish(self.topic_data, self.mqttdata(), True)
            await asyncio.sleep_ms(333)

    async def touch_task(self):
        while not self.exit:
            value = self.touch.endpoint.get()
            if value:
                self.lcd.value = "on" if self.relay.value == 1 else "off"
            await asyncio.sleep_ms(100)


    async def start(self):
        await super().start()
        # self.energy.task = asyncio.create_task(self.energy_task())
        self.lcd.task = asyncio.create_task(self.lcd_task())
        self.lux.task = asyncio.create_task(self.lux_task())
        self.switch.task = asyncio.create_task(self.switch_task())
        self.touch.task = asyncio.create_task(self.touch_task())
        self.relay.task = asyncio.create_task(self.relay_task())

    def deinit(self):
        super().deinit()
        # self.energy.task.cancel()
        self.lcd.task.cancel()
        self.lcd.endpoint.clear()
        self.lux.task.cancel()
        self.switch.task.cancel()
        self.touch.task.cancel()
        self.relay.task.cancel()

    @staticmethod
    def fmt4(x: float) -> str:
        def _n_dec(number: float) -> int:
            n_int = len(str(int(number))) if number >= 1 else 0
            return 3 if number < 1 else (4 - n_int)

        number = abs(x) if x else 0.0

        if number == 0.0:
            return "0.000"
        elif number >= 1000:
            return ("-" if x < 0 else "")  + str(int(number))[:4]

        rounded = round(number, _n_dec(number))
        n_dec = _n_dec(rounded)
        rounded = round(number, n_dec)

        return ("-" if x < 0 else "") + ("{0:." + str(n_dec) + "f}").format(rounded)


if __name__ == "__main__":
    OutletApplication().run()

