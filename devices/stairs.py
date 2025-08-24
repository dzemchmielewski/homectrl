import asyncio
import json
import logging

from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin, PWM
from toolbox.bmp_aht import BMP_AHT

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class StairsApplication(BoardApplication):
    def __init__(self):
        BoardApplication.__init__(self, 'stairs')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.darkness = False

        self.light = Facility("light", PWM(Pin(2), 5000))
        self.light.endpoint.duty(0)

        self.conditions = Facility("conditions", BMP_AHT.from_pins(14, 15),
                                   lambda x: {"temperature": x.value[0], "pressure": x.value[1], "humidity": x.value[2]})
        self.conditions.value = (None, None, None)

        self.control = {
            'mode': 'auto'
        }

        self.mqtt_subscriptions["homectrl/onair/darkness/kitchen"] = self.darkness_message


    def read(self, to_json = True):
        result = (self.light.to_dict()
                  | self.conditions.to_dict()
                  | {
                      'darkness': self.darkness,
                      'control': self.control,
                  })
        return json.dumps(result) if to_json else result

    def darkness_message(self, topic, message, retained):
        self.log.info(f"Darkness message received: topic='{topic}', message='{message}', retained={retained}")
        self.darkness = bool(json.loads(message)['value'])

    async def light_task(self):
        while not self.exit:
            if self.control['mode'] == "auto":
                #TODO: implement auto mode
                light = 0
            elif self.control['mode'] == "on":
                light = 1
            elif self.control['mode'] == "off":
                light = 0
            else:
                raise ValueError(f"Unknown mode: {self.control['mode']}")

            if light != self.light.value:
                self.light.value = light
                # TODO: make it more sophisticated (darker in the night)
                self.light.endpoint.duty(light * 1023)
                await self.publish(self.topic_data, self.read(to_json=False), True)

            await asyncio.sleep_ms(200)

    async def conditions_task(self):
        while not self.exit:
            readings = self.conditions.endpoint.readings()
            if readings != self.conditions.value:
                self.conditions.value = readings
                await self.publish(self.topic_data, self.read(False), True)
            await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self.light.task = asyncio.create_task(self.light_task())
        self.conditions.task = asyncio.create_task(self.conditions_task())

    def deinit(self):
        super().deinit()
        self.light.endpoint.deinit()
        self.light.task.cancel()
        self.conditions.task.cancel()

