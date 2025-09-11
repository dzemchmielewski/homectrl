import asyncio
import json
import logging
import time

from micropython import const

from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin, PWM

from pwm_fade import PWMFade

logging.basicConfig(level=logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))


class StairsApplication(BoardApplication):

    # PROD:
    CONF_USE_MQTT = const(True)
    CONF_LIGHT_PIN = const(2)
    CONF_PRESENCE_UP_PIN = const(35)
    CONF_PRESENCE_DOWN_PIN = const(12)
    CONF_LIGHT_TIMEOUT = const(20_000)

    # # DEV:
    # CONF_USE_MQTT = const(False)
    # CONF_LIGHT_PIN = const(0)
    # CONF_PRESENCE_UP_PIN = const(21)
    # CONF_PRESENCE_DOWN_PIN = const(20)
    # CONF_LIGHT_TIMEOUT = const(5_000)

    BRIGHTNESS = {
        (0, 5): 5,
        (6, 21): 40,
        (21, 21): 30,
        (22, 22): 20,
        (23, 23): 10,
    }

    def __init__(self):
        BoardApplication.__init__(self, 'stairs', use_mqtt=self.CONF_USE_MQTT)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.darkness = Facility("darkness")

        self.light = Facility("light", PWMFade(PWM(Pin(self.CONF_LIGHT_PIN), 5000)), value=False, register_access=False)
        self.light.endpoint.pwm.duty(0)

        self.presence_up = Facility("presence_up", endpoint=Pin(self.CONF_PRESENCE_UP_PIN, Pin.IN, Pin.PULL_DOWN), value=False)
        self.presence_down = Facility("presence_down", endpoint=Pin(self.CONF_PRESENCE_DOWN_PIN, Pin.IN, Pin.PULL_DOWN), value=False)
        self.presence = Facility("presence", value=False)

        if self.CONF_USE_MQTT:
            self.mqtt_subscriptions["homectrl/onair/darkness/kitchen"] = self.darkness_message
        else:
            self.darkness.value = True

        self.publish_mqtt = Facility("publish_mqtt", value=False)

        # self.conditions = Facility("conditions", BMP_AHT.from_pins(14, 15, calibrate_pressure=2.6),
        #                            lambda x: {"temperature": x.value[0], "pressure": x.value[1], "humidity": x.value[2]})
        # self.conditions.value = (None, None, None)

        # self.control = {
        #     'mode': 'auto'
        # }



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

    async def publish_mqtt_task(self):
        while not self.exit:
            if self.publish_mqtt.value:
                await self.publish(self.topic_data, self.read(to_json=False), True)
                self.publish_mqtt.value = False
            await asyncio.sleep_ms(100)

    def darkness_message(self, topic, message, retained):
        self.log.info(f"Darkness message received: topic='{topic}', message='{message}', retained={retained}")
        if self.darkness.value is not None:
            self.publish_mqtt.value = True
        self.darkness.value = bool(json.loads(message)['value'])

    def _calc_brightness(self) -> float:
        (hour, minute) = time.localtime()[3:5]
        for (start, end), value in self.BRIGHTNESS.items():
            if start <= hour <= end:
                return value
        return 0.0

    def _calc_fadein(self, brightness: float):
        return max(20/2, brightness / 2)

    def _calc_fadeout(self):
        return self.light.endpoint.to_percent(self.light.endpoint.pwm.duty()) / 5

    async def light_task(self):
        while not self.exit:

            new_presence = self.presence_up.value or self.presence_down.value
            if new_presence != self.presence.value:
                self.presence.value = new_presence
                self.publish_mqtt.value = True

            if self.darkness.value:
                if not self.light.value:
                    if self.presence.value:
                        self.publish_mqtt.value = True
                        self.light.value = True
                        brightness = self._calc_brightness()
                        await self.light.endpoint.fade(brightness, self._calc_fadein(brightness))

                else:
                    # The light is already ACTIVE:
                    if not self.presence.value:
                        # but there is no presence. Time to deactivate the light,
                        # but not immediately - wait for 20 seconds:
                        if time.ticks_diff(time.ticks_ms(), self.presence.set) > self.CONF_LIGHT_TIMEOUT:
                            self.publish_mqtt.value = True
                            self.light.value = False
                            await self.light.endpoint.fade(0, self._calc_fadeout())
                    else:
                        #Keep the light ACTIVE
                        self.light.value = True
            else:
                # It is not dark, so the light must be OFF
                if self.light.value:
                    self.publish_mqtt.value = True
                    self.light.value = False
                    await self.light.endpoint.fade(0, self._calc_fadeout())

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
    #             self.publish_mqtt.value = True
    #         await asyncio.sleep(60)

    async def start(self):
        await super().start()
        self.light.task = asyncio.create_task(self.light_task())
        self.presence_up.task = asyncio.create_task(self.presence_sensor_task(self.presence_up))
        self.presence_down.task = asyncio.create_task(self.presence_sensor_task(self.presence_down))
        self.publish_mqtt.task = asyncio.create_task(self.publish_mqtt_task())
        # self.conditions.task = asyncio.create_task(self.conditions_task())

    def deinit(self):
        super().deinit()
        self.light.endpoint.deinit()
        self.presence_up.task.cancel()
        self.presence_down.task.cancel()
        self.publish_mqtt.task.cancel()
        # self.conditions.task.cancel()

