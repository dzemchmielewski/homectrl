import asyncio
import datetime
import math

import aiohttp
import logging

from backend.services.onairservice import OnAirService
from configuration import Topic
from backend.tools import json_serial, MQTTClient

logger = logging.getLogger("onair.meteo")

class Meteo(OnAirService):

    def __init__(self):
        self.umk_weather_url = "https://pogoda.umk.pl/api/weather"
        self.exit = False

    async def get_umk_weather(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.umk_weather_url) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    logger.debug(await response.text())
                    data = json_resp['data']
                    return {
                        'temperature': round(float(data['tempAir200']['value']), 1),
                        'humidity': round(float(data['airHumidity']['value']), 1),
                        'pressure': round(float(data['atmosphericPressure']['value']), 1),
                        'precipitation': round(float(data['precipitation1']['value']), 1),
                        'wind': round(float(data['windSpeed']['value']), 1),
                       'date': datetime.datetime.fromisoformat(json_resp['dateUTC']).astimezone(),
                        'create_at': datetime.datetime.now(),
                    }
                else:
                    raise Exception(f"Error fetching weather data: {response.status}")

    async def run(self) -> None:
        logger.info(f"URL: {self.umk_weather_url}")
        try:
            while not self.exit:
                try:
                    weather = await self.get_umk_weather()
                    message = json_serial(weather)
                    logger.debug(message)
                    self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo"), message, retain=True)

                    now = datetime.datetime.now()
                    next_minute = math.ceil((now.minute + 1) / 5) * 5
                    if next_minute >= 60:
                        next_run = (now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1))
                    else:
                        next_run = now.replace(minute=next_minute, second=0, microsecond=0)
                    seconds_to_next = (next_run - now).total_seconds()
                    await asyncio.sleep(seconds_to_next)

                except Exception as e:
                    logger.error(f"Error: {e}")
        except KeyboardInterrupt:
            logger.info("Exit...")




