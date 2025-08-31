import asyncio
import json
import logging
import time

from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin, PWM

from pwm_fade import PWMFade

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class StairsApplication(BoardApplication):

    HIGH_BRIGHTNESS = 50
    LOW_BRIGHTNESS = 10
    FADE_IN_SPEED = 50/2
    FADE_OUT_SPEED = 50/5
    LIGHT_TIMEOUT = 20_000

    def __init__(self):
        BoardApplication.__init__(self, 'stairs')
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.darkness = Facility("darkness")

        self.light = Facility("light", PWMFade(PWM(Pin(2), 5000)), value=False, register_access=False)
        #DEV:
        # self.light = Facility("light", PWMFade(PWM(Pin(0), 5000)), value=False, register_access=False)
        self.light.endpoint.pwm.duty(0)

        self.presence_up = Facility("presence_up", endpoint=Pin(35, Pin.IN), value=False)
        self.presence_down = Facility("presence_down", endpoint=Pin(12, Pin.IN), value=False)
        #DEV:
        # self.presence_up = Facility("presence_up", endpoint=Pin(21, Pin.IN, Pin.PULL_DOWN), value=False)
        # self.presence_down = Facility("presence_down", endpoint=Pin(20, Pin.IN, Pin.PULL_DOWN), value=False)
        self.presence = Facility("presence", value=False)

        # self.conditions = Facility("conditions", BMP_AHT.from_pins(14, 15, calibrate_pressure=2.6),
        #                            lambda x: {"temperature": x.value[0], "pressure": x.value[1], "humidity": x.value[2]})
        # self.conditions.value = (None, None, None)

        # self.control = {
        #     'mode': 'auto'
        # }

        self.mqtt_subscriptions["homectrl/onair/darkness/kitchen"] = self.darkness_message


    def read(self, to_json = True):
        result = (self.light.to_dict()
                  # | self.conditions.to_dict()
                  | self.darkness.to_dict()
                  | self.presence_up.to_dict()
                  | self.presence_down.to_dict()
                  | self.presence.to_dict()
                  | self.light.to_dict())
                  # | {
                  #     'control': self.control,
                  # })
        return json.dumps(result) if to_json else result

    def darkness_message(self, topic, message, retained):
        self.log.info(f"Darkness message received: topic='{topic}', message='{message}', retained={retained}")
        self.darkness.value = bool(json.loads(message)['value'])
        # DEV:
        # self.darkness.value = True

    def _light_brightness(self):
        (hour, minute) = time.localtime()[3:5]
        if hour >= 23 or hour < 6:
            return self.LOW_BRIGHTNESS
        return self.HIGH_BRIGHTNESS

    async def light_task(self):
        while not self.exit:
            publish = False
            if self.darkness.value:
                if not self.light.value:
                    if self.presence.value:
                        publish = True
                        self.light.value = True
                        await self.light.endpoint.fade(self._light_brightness(), self.FADE_IN_SPEED)

                else:
                    # The light is already ACTIVE:
                    if not self.presence.value:
                        # but there is no presence. Time to deactivate the light,
                        # but not immediately - wait for 20 seconds:
                        if time.ticks_diff(time.ticks_ms(), self.presence.set) > self.LIGHT_TIMEOUT:
                            publish = True
                            self.light.value = False
                            await self.light.endpoint.fade(0, self.FADE_OUT_SPEED)
                    else:
                        #Keep the light ACTIVE
                        self.light.value = True
                if publish:
                    await self.publish(self.topic_data, self.read(to_json=False), True)
            await asyncio.sleep_ms(100)

    async def presence_task(self):
        while not self.exit:
            new_presence = self.presence_up.value or self.presence_down.value
            if new_presence != self.presence.value:
                self.presence.value = new_presence
                await self.publish(self.topic_data, self.read(to_json=False), True)
            await asyncio.sleep_ms(100)

    async def presence_sensor_task(self, facility: Facility):
        while not self.exit:
            if facility.endpoint.value():
                facility.value = True
            else:
                if facility.value is True:
                    facility.value = False
            await asyncio.sleep_ms(100)

    # async def conditions_task(self):
    #     while not self.exit:
    #         readings = self.conditions.endpoint.readings()
    #         if readings != self.conditions.value:
    #             self.conditions.value = readings
    #             await self.publish(self.topic_data, self.read(False), True)
    #         await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self.light.task = asyncio.create_task(self.light_task())
        self.presence_up.task = asyncio.create_task(self.presence_sensor_task(self.presence_up))
        self.presence_down.task = asyncio.create_task(self.presence_sensor_task(self.presence_down))
        self.presence.task = asyncio.create_task(self.presence_task())
        # self.conditions.task = asyncio.create_task(self.conditions_task())

    def deinit(self):
        super().deinit()
        self.light.endpoint.deinit()
        self.presence_up.task.cancel()
        self.presence_down.task.cancel()
        self.presence.task.cancel()
        # self.conditions.task.cancel()

