#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/../env/bin/python" "$0" "$@"'

import asyncio
import json
import logging
import time

from gpiozero import Button, DigitalOutputDevice, DigitalInputDevice

from backend.devices.attic.pi_application import PiApplication, Facility
from backend.modules.bmp_aht import BMP_AHT

logger = logging.getLogger("attic")
DOORBELL_BUFFER_SECONDS = 3

# D0: 7
# D1: 25
# D2: 24
# D3: 23
# VT: 18
# pull up attic flap 20 relay to read only
# utility room relay 21
#
# horn: 12
#
# LD2410:
# tx/rx uart0
# OUT: 4

# BMP & AHT:
# I2C Bus (1): sda: 2, scl: 3


class AtticApplication(PiApplication):
    def __init__(self):
        super().__init__('attic', use_mqtt=True)
        self.doorbell = Facility("bell", Button(24, pull_up=False), value=False)
        self.doorbell.endpoint.when_pressed = lambda: self.loop.call_soon_threadsafe(self.doorbell.event.set)
        self.horn = Facility("horn", DigitalOutputDevice(12, initial_value=False), value=False)

        self.flap = Facility("doors", DigitalInputDevice(20), value=False)
        self.flap.endpoint.when_activated = lambda: self.loop.call_soon_threadsafe(self.flap.event.set)
        self.flap.endpoint.when_deactivated = lambda: self.loop.call_soon_threadsafe(self.flap.event.set)

        self.presence = Facility("presence", DigitalInputDevice(4), value=False)
        self.presence.endpoint.when_activated = lambda: self.loop.call_soon_threadsafe(self.presence.event.set)
        self.presence.endpoint.when_deactivated = lambda: self.loop.call_soon_threadsafe(self.presence.event.set)

        self.utlility_light = DigitalOutputDevice(21)

        import serial
        from backend.devices.attic.ld2410 import LD2410
        try:
            self.radar = LD2410(serial.Serial(
                port='/dev/ttyAMA0',   # or /dev/serial0, /dev/ttyUSB0 for USB adapter
                baudrate=256000,
                bytesize=8,            # bits=8
                parity=serial.PARITY_NONE,  # parity=None
                stopbits=1,            # stop=1
                timeout=1
            ))
        except Exception as e:
            logger.fatal(f"LD2410 radar error while loading: {e}")
            self.radar = None

        try:
            sensor = BMP_AHT.from_bus(1)
        except Exception as e:
            logger.fatal(f"BMPAHT error while loading: {e}")
            sensor = None
        self.conditions = Facility("conditions", sensor, value=(None, None, None),
                                   to_dict=lambda x: {
                                       "temperature": x.value[0],
                                       "pressure": x.value[1],
                                       "humidity": x.value[2]})

    def read(self, to_json: bool = True) -> dict | str:
        result = (self.doorbell.to_dict()
                  | self.flap.to_dict()
                  | self.presence.to_dict()
                  | self.conditions.to_dict())
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
                self.doorbell.value = True
                logger.info("ding dong")
                await self.publish(self.topic_state, self.read(False), retain=False)
                await self.horn_signal()
                self.doorbell.value = False
                await self.publish(self.topic_state, self.read(False), retain=False)

    async def flap_task(self):
        while not self.exit:
            await self.flap.event.wait()
            value = self.flap.endpoint.value
            self.flap.event.clear()
            if value != self.flap.value:
                self.flap.value = value
                logger.info(f"flap: ({self.flap.value})")
                await self.publish(self.topic_state, self.read(False), retain=True)

    async def presence_task(self):
        while not self.exit:
            await self.presence.event.wait()
            value = self.presence.endpoint.value
            self.utlility_light.value = value
            self.presence.event.clear()
            if value != self.presence.value:
                self.presence.value = value
                logger.info(f"presence: ({self.presence.value})")
                if self.radar:
                    #(target_type, moving_target_dist, moving_target_energy, static_target_dist, static_target_energy, detection_dist)
                    data = self.radar.get_radar_data()
                    logger.info(data)
                    r = { "radar": {
                            "presence": value,
                            "target_state": data[0][0],
                            "move": {
                                "distance": data[0][1],
                                "energy": data[0][2],
                            },
                            "static": {
                                "distance": data[0][3],
                                "energy": data[0][4],
                            },
                            "distance": data[0][5]
                    }}
                    await self.publish(self.topic_state, self.read(False) | r, retain=True)

                else:
                    await self.publish(self.topic_state, self.read(False), retain=True)

                # Temporary monitoring of values when presence is on:
                while self.presence.endpoint.value == 1:
                    logger.info(self.radar.get_radar_data())
                    await asyncio.sleep(1)


    async def conditions_task(self):
        if self.conditions.endpoint is not None:
            while not self.exit:
                c = self.conditions.endpoint.readings()
                if c != self.conditions.value:
                    self.conditions.value = c
                    await self.publish(self.topic_state, self.read(False), retain=True)
                await asyncio.sleep(60)

    async def start(self):
        logger.debug("start")
        self.doorbell.task = asyncio.create_task(self.doorbell_task())
        self.flap.task = asyncio.create_task(self.flap_task())
        self.presence.task = asyncio.create_task(self.presence_task())

        self.conditions.task = asyncio.create_task(self.conditions_task())

if __name__ == "__main__":
    AtticApplication().run()
