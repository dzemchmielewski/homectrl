import asyncio
import json
import logging

import time
from board.board_application import BoardApplication, Facility
from configuration import Configuration
from display_meteomini import MeteoMiniDisplay
from machine import Pin, SPI, deepsleep
from ssd1680 import SSD1680_2_13_in
from toolbox.pinio import PinIO

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class MeteoMiniApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'meteomini')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.SLEEP_TIME_SEC = None
        # self.SLEEP_TIME_SEC = 15

        cs, dc, rst, busy = Pin(1, Pin.OUT), Pin(2, Pin.OUT), Pin(3, Pin.OUT), Pin(4, Pin.IN)
        spi = SPI(1, baudrate=1_000_000, sck=Pin(0), mosi=Pin(21))
        self.log.info(f"SPI Device init. Pins: CS={cs}, DC={dc}, RST={rst}, BUSY={busy}, SPI={spi}")
        self.ssd = SSD1680_2_13_in(spi, cs, dc, rst, busy, orientation='landscape')
        self.log.info(f"Framebuffer: {self.ssd.fb_width} x {self.ssd.fb_height}, mode={self.ssd.fb_mode}")
        meteo = MeteoMiniDisplay(self.ssd.fb_width, self.ssd.fb_height, self.ssd.fb_mode)
        self.display = Facility("display", meteo, {'meteo': None, 'astro': None})
        self.indicator = Facility("indicator", PinIO(20, 1), 1)
        self.push = Facility("push", PinIO(10, pull=Pin.PULL_DOWN), False)
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/meteo"] = self.meteo_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/astro"] = self.astro_message
        self.mqtt_custom_config['keepalive'] = 400
        self.capabilities = {
            "controls": [
                {
                    "name": "sleep",
                    "type": "bool",
                }
            ]}
        self.control = {
            'sleep': False
        }

    def read(self, to_json = True):
        result = (self.display.to_dict()
                  | {'sleep': self.control['sleep']}
                  )
        return json.dumps(result) if to_json else result

    def meteo_message(self, topic, message, retained):
        self.log.info(f"Meteo message received.")
        self.display.value['meteo'] = json.loads(message)
        self.display.value = self.display.value  # trigger update

    def astro_message(self, topic, message, retained):
        self.log.info(f"Astro message received.")
        self.display.value['astro'] = json.loads(message)
        self.display.value = self.display.value  # trigger update

    async def display_task(self):
        last_update = None
        first = True
        while not self.exit:
            values = self.display.value
            if values['meteo'] is not None and values['astro'] is not None:

                if (last_update is None or last_update != self.display.set) or self.push.value:
                    if self.push.value:
                        self.log.info("Display update triggered by the push button.")
                        self.push.value = False
                    else:
                        self.log.info("Display update triggered by new data.")

                    last_update = self.display.set
                    self.display.endpoint.update(values['meteo'], values['astro'])

                    self.log.info("Display updating...")

                    # For unknown reasons, the first update after power is not working.
                    # So we initialize the display once again here.
                    # That's ridiculous, but it works.
                    if first:
                        first = False
                        cs, dc, rst, busy = Pin(1, Pin.OUT), Pin(2, Pin.OUT), Pin(3, Pin.OUT), Pin(4, Pin.IN)
                        spi = SPI(1, baudrate=1_000_000, sck=Pin(0), mosi=Pin(21))
                        self.log.info(f"SPI Device init. Pins: CS={cs}, DC={dc}, RST={rst}, BUSY={busy}, SPI={spi}")
                        self.ssd = SSD1680_2_13_in(spi, cs, dc, rst, busy, orientation='landscape')

                    self.ssd.display(self.display.endpoint.fb)
                    self.log.info("Display updating done.")
                    await asyncio.sleep(1)

                    if self.control['sleep']:
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

            await asyncio.sleep(1)

    async def push_task(self):
        last_value = self.push.endpoint.get()
        while not self.exit:
            value = self.push.endpoint.get()
            if value != last_value:
                last_value = value
                self.log.info(f"Push button changed: {value}")
                self.indicator.endpoint.toggle()
                if value == 1:
                    self.push.value = True
                    await asyncio.sleep_ms(1_000)
            await asyncio.sleep_ms(100)

    async def start(self):
        await super().start()
        self.display.task = asyncio.create_task(self.display_task())
        self.push.task = asyncio.create_task(self.push_task())

    def deinit(self):
        super().deinit()
        self.display.task.cancel()
        self.push.task.cancel()
        self.indicator.endpoint.off()

if __name__ == "__main__":
    MeteoMiniApplication().run()
