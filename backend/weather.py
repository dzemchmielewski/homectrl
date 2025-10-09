import asyncio
import datetime
import random

import aiohttp
import logging
from configuration import Topic
from backend.tools import json_serial, MQTTClient


class Weather:

    def __init__(self):
        self.umk_weather_url = "https://pogoda.umk.pl/api/weather"
        self.exit = False
        self.mqtt = MQTTClient(keepalive=11 * 60)

    async def get_umk_weather(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.umk_weather_url) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    data = json_resp['data']
                    return {
                        'temperature': round(float(data['tempAir200']['value']), 1),
                        'humidity': round(float(data['airHumidity']['value']), 1),
                        'pressure': round(float(data['atmosphericPressure']['value']), 1),
                    }
                else:
                    raise Exception(f"Error fetching weather data: {response.status}")

    async def go(self) -> None:
        logging.info(f"URL: {self.umk_weather_url}")
        try:
            while not self.exit:
                try:
                    now = datetime.datetime.now()
                    next_minute = ((now.minute // 10) + 1) * 10
                    if next_minute >= 60:
                        next_hour = now.replace(hour=(now.hour + 1) % 24, minute=0, second=0, microsecond=0)
                    else:
                        next_hour = now.replace(minute=next_minute, second=0, microsecond=0)
                    seconds_to_next = (next_hour - now).total_seconds()
                    await asyncio.sleep(seconds_to_next)

                    weather = await self.get_umk_weather()
                    logging.info(weather)
                    self.mqtt.publish(Topic.Device.format('umk', Topic.Device.Facility.data), json_serial(weather), retain=True)

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
