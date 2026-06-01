#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/../env/bin/python" "$0" "$@"'

import asyncio
import json
import logging
import time

from gpiozero import Button, DigitalOutputDevice

from backend.devices.attic.pi_application import PiApplication, Facility

logger = logging.getLogger("attic")
DOORBELL_BUFFER_SECONDS = 3

# D0: 22
# D1: 24
# D2: 25
# D3: 5
# VT: 6
# horn: 12

class AtticApplication(PiApplication):
    def __init__(self):
        super().__init__('attic')
        self.doorbell = Facility("doorbell", Button(25), value=0)
        self.doorbell.endpoint.when_pressed = lambda: self.loop.call_soon_threadsafe(self.doorbell.event.set)
        self.horn = Facility("horn", DigitalOutputDevice(12, initial_value=False), value=False)

    def read(self, to_json: bool = True) -> dict | str:
        result = self.doorbell.to_dict()
        return json.dumps(result) if to_json else result

    async def horn_signal(self):
        logger.info(f"HORN on")
        for s,w in [(0.2, 0.1), (0.7, 0)]:
            self.horn.endpoint.on()
            await asyncio.sleep(s)
            self.horn.endpoint.off()
            await asyncio.sleep(w)
        logger.info(f"HORN off")

    async def doorbell_task(self):
        while not self.exit:
            await self.doorbell.event.wait()
            self.doorbell.event.clear()
            if self.doorbell.set is None or self.doorbell.set + DOORBELL_BUFFER_SECONDS < time.time():
                self.doorbell.value += 1
                logger.info(f"ding dong ({self.doorbell.value})")
                await self.publish(self.topic_state, self.read(False) | {'dingdong': True}, retain=False)
                await self.horn_signal()

    async def start(self):
        logger.debug("start")
        self.doorbell.task = asyncio.create_task(self.doorbell_task())

if __name__ == "__main__":
    AtticApplication().run()
