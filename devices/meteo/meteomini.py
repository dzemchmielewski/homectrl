import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


import time
from board.board_application import BoardApplication, Facility
from board.boot import Boot
from configuration import Configuration
from display_meteomini import MeteoMiniDisplay
from machine import Pin, SPI, SoftI2C, deepsleep
from max17043 import MAX17043
from ssd1680 import SSD1680_2_13_in


class MeteoMiniApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'meteomini')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.SLEEP_TIME_SEC = None
        # self.SLEEP_TIME_SEC = 15

        spi = SPI(1, baudrate=1_000_000, sck=Pin(4), mosi=Pin(21))
        self.ssd = SSD1680_2_13_in(spi, *self.dspl_pins(), orientation='landscape')
        self.log.info(f"Framebuffer: {self.ssd.fb_width} x {self.ssd.fb_height}, mode={self.ssd.fb_mode}")
        meteo = MeteoMiniDisplay(self.ssd.fb_width, self.ssd.fb_height, self.ssd.fb_mode)
        self.display = Facility("display", meteo, {'meteo': None, 'astro': None, 'battery': None})

        # Battery support (from meteo.py)
        self.battery = Facility("battery", MAX17043(SoftI2C(scl=Pin(7), sda=Pin(9))),
                                to_dict=lambda x : {'battery': {'value': x.value[0], 'voltage': x.value[1]}})

        # Indicator
        self.indicator = Facility("indicator", Pin(5, Pin.OUT), 1)
        self.indicator.endpoint.on()

        # MQTT subscriptions
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR}/meteo/current"] = self.meteo_message
        self.mqtt_subscriptions[f"{Configuration.TOPIC_HOMECTRL_ONAIR_ACTIVITY}/astro"] = self.astro_message
        self.mqtt_custom_config['keepalive'] = 400

        # Capabilities and control
        self.capabilities = {
            "controls": [
                {
                    "name": "sleep",
                    "type": "bool",
                }
            ]}
        self.control = {
            'sleep': True
        }

    def dspl_pins(self):
        # cs, dc, rst, busy
        return (Pin(3, Pin.OUT), Pin(2, Pin.OUT), Pin(1, Pin.OUT), Pin(0, Pin.IN))

    def read(self, to_json = True):
        result = (self.display.to_dict()
                  | self.battery.to_dict()
                  | {'sleep': self.control['sleep']}
                  )
        return json.dumps(result) if to_json else result

    def meteo_message(self, topic, message, retained):
        self.log.info(f"Meteo message received.")
        self.display.value['meteo'] = json.loads(message)['data']
        self.display.value = self.display.value  # trigger update

    def astro_message(self, topic, message, retained):
        self.log.info(f"Astro message received.")
        self.display.value['astro'] = json.loads(message)
        self.display.value = self.display.value  # trigger update

    def data_complete(self):
        values = self.display.value
        return (values['meteo'] is not None
            and values['astro'] is not None
            and values['battery'] is not None)

    async def display_task(self):
        last_update = None
        first = True
        while not self.exit:
            if self.data_complete():
                if (last_update is None or last_update != self.display.set) or self.push.value:
                    self.log.info("Display update triggered by new data.")

                    last_update = self.display.set
                    self.display.endpoint.update(self.display.value)

                    self.log.info("Display updating...")

                    # For unknown reasons, the first update after power is not working.
                    # So we initialize the display once again here.
                    # That's ridiculous, but it works.
                    if first:
                        first = False
                        spi = SPI(1, baudrate=1_000_000, sck=Pin(4), mosi=Pin(21))
                        self.ssd = SSD1680_2_13_in(spi, *self.dspl_pins(), orientation='landscape')

                    self.ssd.display(self.display.endpoint.fb)
                    self.log.info("Display updating done.")
                    await asyncio.sleep(1)

                    if self.control['sleep']:
                        await self.go_sleep()

            await asyncio.sleep(1)
            if self.control['sleep'] and (time.time_ms() - Boot.get_instance().load_time)  > 60 * 5 * 1_000:
                # After 5 minutes  there was no screen update
                # - probably the issue with receiving MQTT messages
                # Therefore go to sleep and try again later
                await self.go_sleep()

    async def battery_task(self):
        last_mqtt = None
        while not self.exit:
            self.battery.value = (round(self.battery.endpoint.soc), self.battery.endpoint.voltage)
            if self.battery.value[0] > 100:
                self.battery.value[0] = 100
            self.display.value['battery'] = self.battery.value[0]
            self.display.value = self.display.value  # trigger update
            self.log.info(f"Battery: {self.battery.value[0]}%, {self.battery.value[1]:.2f}V")
            if last_mqtt is None or (time.time_ms() - last_mqtt) > 60 * 5 * 1_000:
                await self.publish(self.topic_data, self.battery.to_dict(), True)
                last_mqtt = time.time_ms()
            await asyncio.sleep(60)  # every 1 minute

    async def go_sleep(self):
        if self.SLEEP_TIME_SEC:
            seconds_to_next = self.SLEEP_TIME_SEC
        else:
            _, _, _, _, min, sec, _, _ = time.localtime()
            next_minute = ((min + 5) // 5) * 5
            seconds_to_next = ((next_minute - min) * 60 - sec) + 45

        self.log.info(f"Going to sleep now. Seconds to wakeup: {seconds_to_next}")
        self.indicator.endpoint.off()
        await asyncio.sleep(1)
        # Put into the deep sleep:
        deepsleep(seconds_to_next * 1_000)

    async def start(self):
        await super().start()
        self.display.task = asyncio.create_task(self.display_task())
        self.battery.task = asyncio.create_task(self.battery_task())

    def deinit(self):
        super().deinit()
        self.display.task.cancel()
        self.battery.task.cancel()
        self.indicator.endpoint.off()

if __name__ == "__main__":
    MeteoMiniApplication().run()