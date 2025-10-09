import asyncio
import random

import aiohttp
import logging
from configuration import Topic
from backend.tools import json_serial, MQTTClient


class Weather:

    def __init__(self):
        self.umk_weather_url = "https://pogoda.umk.pl/api/weather"
        self.exit = False
        self.mqtt = MQTTClient()

    async def get_umk_weather(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.umk_weather_url) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    data = json_resp['data']
                    return {
                        'temperature': float(data['tempAir200']['value']) + random.randint(-1, 1)*0.1,
                        'humidity': float(data['airHumidity']['value']),
                        'pressure': float(data['atmosphericPressure']['value']),
                    }
                else:
                    raise Exception(f"Error fetching weather data: {response.status}")

    async def go(self) -> None:
        logging.info(f"URL: {self.umk_weather_url}")
        try:
            while not self.exit:
                try:
                    weather = await self.get_umk_weather()
                    logging.info(weather)
                    self.mqtt.publish(Topic.Device.format('umk', Topic.Device.Facility.data), json_serial(weather), retain=True)
                    # await asyncio.sleep(10*60) # Sleep for 10 minutes
                    await asyncio.sleep(10)
                except Exception as e:
                    logging.error(f"Error: {e}")
        except KeyboardInterrupt:
            logging.info("Exit...")

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.go())
        loop.close()

if __name__ == "__main__":
    Weather().start()
