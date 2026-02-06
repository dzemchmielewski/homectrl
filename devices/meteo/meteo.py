import logging
logging.basicConfig(level=logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

import asyncio
import json
import gc
import sys

import time
from framebuf import GS2_HMSB
from machine import Pin, SPI, deepsleep, SoftI2C

from board.board_application import BoardApplication, Facility
from toolbox.pinio import PinIO

from configuration import Configuration
from max17043 import MAX17043
from epd7in5v2 import EPD7in5V2
from display_meteo import MeteoDisplay


class MeteoApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'meteo')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.SLEEP_TIME_SEC = None
        # self.SLEEP_TIME_SEC = 15

        spi = SPI(1, baudrate=4_000_000, sck=Pin(5), mosi=Pin(4))
        cs = Pin(6, Pin.OUT)
        dc = Pin(7, Pin.OUT)
        rst = Pin(0, Pin.OUT)
        busy = Pin(1, Pin.IN, Pin.PULL_UP)
        pwr = Pin(8, Pin.OUT)
        self.log.info(f"SPI Device init. Pins: CS={cs}, DC={dc}, RST={rst}, BUSY={busy}, SPI={spi}")

        width, height, mode = 800, 480, GS2_HMSB

        self.epd = EPD7in5V2(width, height, spi, cs, dc, rst, busy, pwr)

        self.indicator = Facility("indicator", PinIO(10, 1), 1)
        self.battery = Facility("battery", MAX17043(SoftI2C(scl=Pin(18), sda=Pin(9))),
                                to_dict=lambda x : {'battery': {'value': x.value[0], 'voltage': x.value[1]}})
        # boolean display value: True = display is processing refresh, False = idle
        self.display = Facility("display", MeteoDisplay(width, height, mode))
        self.display.value = True

        btn = PinIO(21, pull=Pin.PULL_DOWN)
        self.sleep_btn = Facility("sleep_btn", endpoint=btn, value=btn.get())

        self.trigger = Facility("trigger", None, value={
            'update': True,
            'sleep': False,
        })

        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/meteo"] = self.data_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/astro"] = self.data_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/holidays"] = self.data_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/meteofcst"] = self.data_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/meteo/temperature"] = self.temperature_message
        self.mqtt_custom_config['keepalive'] = 400

        self.data = {
            'meteo': None,
            'astro': None,
            'holidays': None,
            'meteofcst': None,
            'temperature': None,
            'battery': None,
        }

    def data_complete(self):
        return (self.data['meteo'] is not None
                and self.data['astro'] is not None
                and self.data['holidays'] is not None
                and self.data['meteofcst'] is not None
                and self.data['temperature'] is not None
                and self.data['battery'] is not None
                )

    def read(self, to_json = True):
        result = (self.trigger.to_dict()
                  | self.sleep_btn.to_dict()
                  | self.indicator.to_dict()
                  | self.display.to_dict()
                  | self.battery.to_dict())
        return json.dumps(result) if to_json else result

    def data_message(self, topic, message, retained):
        name = topic.split('/')[-1]
        self.log.info(f"Message received. Name: {name}")
        if name == 'meteofcst':
            self.data['meteofcst'] = json.loads(message)['meteofcst']
        else:
            self.data[name]  = json.loads(message)

        if name == 'astro':
            from_day_offset = -1
            to_day_offset = 4
            # Pick only 5 days of astro data:
            self.data['astro']['astro'] = [astro_data for astro_data in self.data['astro']['astro'] if astro_data['day']['day_offset'] in range(from_day_offset, to_day_offset)]

    def temperature_message(self, topic, message, retained):
        self.data['temperature'] = json.loads(message)

    def trigger_update(self, value = True):
        self.trigger.value['update'] = value
        self.trigger.value = self.trigger.value

    def trigger_sleep(self, value = True, force = False):
        if value and force:
            self.display.value = False
        self.trigger.value['sleep'] = value
        self.trigger.value = self.trigger.value

    async def handle_error(self, e, start_over = False):
        try:
            await self.publish(self.topic_live,{"live": True, 'error': f"error: {e}"}, False)
            with open("crash.log", 'w' if start_over else 'a') as f:
                if isinstance(e, Exception):
                    sys.print_exception(e, f)
                else:
                    f.write(str(e))
                f.write("\n---\n")
        except:
            pass

    async def display_task(self):
        while not self.exit:

            try:
                if self.trigger.value['update'] and self.data_complete():
                    self.log.info("Display update triggered.")
                    self.trigger.value['update'] = False
                    self.trigger.value = self.trigger.value
                    self.display.value = True
                    self.display.endpoint.update(self.data)
                    try:
                        gc.collect()
                        await asyncio.sleep(0.2)  # let gc do the job
                        self.epd.init(self.display.endpoint.fb.mode)
                        self.epd.display(self.display.endpoint.fb)
                    finally:
                        self.epd.deinit(False)
                    await asyncio.sleep(1)

                    self.display.value = False
                    self.trigger_sleep()

                if (time.time_ms() - self.display.set)  > 60 * 5 * 1_000 and self.sleep_btn.value:
                    # After 5 minutes  there was no screen update and sleep button is ON
                    # so the break was intentional. Time to refresh the display:
                    self.trigger_update()

                await asyncio.sleep(1)

            except Exception as e:
                self.handle_error(e)
                await self.publish(self.topic_live,{"live": True, 'error': f"error: {e}"}, False)
                # self.trigger_sleep(force=True)

    def go_sleep(self):
        if self.SLEEP_TIME_SEC:
            seconds_to_next = self.SLEEP_TIME_SEC
        else:
            _, _, _, _, min, sec, _, _ = time.localtime()
            next_minute = ((min + 5) // 5) * 5
            seconds_to_next = ((next_minute - min) * 60 - sec) + 45

        self.log.info(f"Going to sleep now. Seconds to wakeup: {seconds_to_next}")
        self.indicator.endpoint.off()
        # Put into the deep sleep:
        deepsleep(seconds_to_next * 1_000)

    async def guard_task(self):
        while not self.exit:
            if self.display.value:
                if (time.time_ms() - self.display.set) > 30 * 1_000:
                    # If display is busy for more than 30 second - most likely it hanged
                    # on device busy pin. Log error and go sleep, good luck after wakeup.
                    self.handle_error("Display busy for more than 30 seconds - going to sleep.")
                    self.trigger_sleep(force=True)
            else:  # display is idle
                if not self.sleep_btn.value and (time.time_ms() - self.display.set) > 60 * 3 * 1_000:
                    # If display is idle for more than 3 minutes and sleep button is not ON
                    # then probably there is an issue with getting all MQTT messages
                    # Log error and go sleep, good luck after wakeup.
                    self.handle_error("Display idle for more than 3 minutes - going to sleep.")
                    self.trigger_sleep(force=True)
            await asyncio.sleep(1)

    async def battery_task(self):
        last_mqtt = None
        while not self.exit:
            self.battery.value = (round(self.battery.endpoint.soc), self.battery.endpoint.voltage)
            if self.battery.value[0] > 100:
                self.battery.value[0] = 100
            self.data['battery'] = self.battery.value[0]
            if last_mqtt is None or (time.time_ms() - last_mqtt) > 60 * 5 * 1_000:
                await self.publish(self.topic_data, self.battery.to_dict(), True)
                last_mqtt = time.time_ms()
            await asyncio.sleep(60)  # every 1 minute

    async def sleep_btn_task(self):
        while not self.exit:
            value = self.sleep_btn.endpoint.get()
            if value != self.sleep_btn.value:
                self.sleep_btn.value = value
                self.log.info(f"Sleep switch changed. New value: {self.sleep_btn.value}")
                if self.sleep_btn.value == 0:
                    # if sleep button has been turned ON -trigger the sleep
                    self.trigger_sleep()
            await asyncio.sleep(0.2)

    async def trigger_task(self):
        while not self.exit:
            if self.trigger.value['sleep']:
                if self.sleep_btn.value:
                    # reset sleep trigger if sleep button is ON
                    self.trigger_sleep(False)
                else:
                    if not self.display.value:
                        self.go_sleep()
            await asyncio.sleep(1)

    async def start(self):
        await super().start()
        self.display.task = asyncio.create_task(self.display_task())
        self.battery.task = asyncio.create_task(self.battery_task())
        self.sleep_btn.task = asyncio.create_task(self.sleep_btn_task())
        self.trigger.task = asyncio.create_task(self.trigger_task())
        self.indicator.task = asyncio.create_task(self.guard_task())

def deinit(self):
        super().deinit()
        self.display.task.cancel()
        self.battery.task.cancel()
        self.sleep_btn.task.cancel()
        self.trigger.task.cancel()
        self.indicator.task.cancel()
        self.indicator.endpoint.off()

if __name__ == "__main__":
    MeteoApplication().run()
