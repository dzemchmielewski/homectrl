import asyncio
import json
import logging

logging.basicConfig(level=logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))

from board.board_application import BoardApplication, Facility
from configuration import Configuration
from machine import Pin, PWM
from pwm_fade import PWMFade, PWMArray


#PWM_PINS = [20,21,47,48,15,0,35,36]
PWM_PINS = [4, 5, 6, 7, 15, 17, 18, 8]
SWITCH_PIN = 14
SIZE = len(PWM_PINS)
DEFAULT_BRIGHTNESS = 40

class KLampApplication(BoardApplication):

    def __init__(self):

        BoardApplication.__init__(self, 'klamp', use_mqtt=True)
        (_, self.topic_data, _, _, _) = Configuration.topics(self.name)

        self.publish_mqtt = asyncio.Event()

        self.capabilities = {
            "controls":
                [
                    {
                        "name": f"brightness",
                        "type": "list",
                    }
                ]}

        self.control = (
                {
                'brightness': [DEFAULT_BRIGHTNESS] * SIZE
                })

        self.switch = Facility("switch", Pin(SWITCH_PIN, Pin.IN, Pin.PULL_DOWN), False, register_access=False)
        self.switch.endpoint.irq(handler=self.click, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self.switch.value = self.switch.endpoint.value()

        self.lights = Facility("lights",
                               PWMArray([PWMFade(PWM(Pin(p), 5000)) for p in PWM_PINS], [DEFAULT_BRIGHTNESS] * SIZE),
                               value=False,
                               register_access=False)

    def click(self, pin):
        self.switch.value = pin.value()

    def read(self, to_json = True):
        result = {
            "transient_light": self.lights.value,
        }
        return json.dumps(result) if to_json else result

    async def light_task(self):
        while not self.exit:
            await self.lights.endpoint.chng_brightness(self.control['brightness'], 2)

            if self.switch.value:  # ON!
                if not self.lights.value:
                    self.log.info("LIGHT  ON")
                    self.lights.value = True
                    # We do not need to publish mode change. That is known externally
                    # self.publish_mqtt.set()
                    await self.lights.endpoint.fadein(2)

            else:  # OFF!
                if self.lights.value:
                    self.log.info("LIGHT OFF")
                    self.lights.value = False
                    # We do not need to publish mode change. That is known externally
                    # self.publish_mqtt.set()
                    await self.lights.endpoint.fadeout(5)

            await asyncio.sleep_ms(100)

    async def publish_mqtt_task(self):
        await self.publish_capabilities_task()
        while not self.exit:
            await self.publish_mqtt.wait()
            self.publish_mqtt.clear()
            await self.publish(self.topic_data, self.read(to_json=False), True)

    async def publish_capabilities_task(self):
        while self.mqtt is None or not self.mqtt.is_initially_connected:
            await asyncio.sleep_ms(1000)
        await self.publish(self.topic_state, self.control, True)
        await self.publish(self.topic_capabilities, self.capabilities, True)

    async def start(self):
        await super().start()
        self.lights.task = asyncio.create_task(self.light_task())
        self.publish_mqtt.task = asyncio.create_task(self.publish_mqtt_task())

    def deinit(self):
        super().deinit()
        self.lights.task.cancel()
        self.publish_mqtt.task.cancel()
        self.lights.endpoint.deinit()

if __name__ == "__main__":
    KLampApplication().run()
