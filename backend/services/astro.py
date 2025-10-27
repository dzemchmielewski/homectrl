import asyncio
from datetime import date, time, datetime, timedelta

import aiohttp
import logging

from backend.services.onairservice import OnAirService
from configuration import Topic
from backend.tools import json_serial

logger = logging.getLogger("onair.astro")

class Astro(OnAirService):

    def __init__(self):
        self.url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/Toru%C5%84"
        self.token = "5N9S8EP7U3XQC6PVVEV4G5XV4"
        self.exit = False

    async def get_data(self, day: date) -> dict:
        d_from = (day - timedelta(days=1)).strftime("%Y-%m-%d")
        d_to = (day + timedelta(days=5)).strftime("%Y-%m-%d")
        logger.info("External call: " + d_from + " - " + d_to)
        url = (self.url
               + "/" + d_from + "/" + d_to
               + "?unitGroup=metric&key=" + self.token
               + "&contentType=json&elements=datetime,moonphase,sunrise,sunset,moonrise,moonset")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(await response.text())
                    astro_data = []
                    for day in data["days"]:
                        the_day = datetime.strptime(day["datetime"], "%Y-%m-%d").date()
                        astro_day = {
                            'date': the_day,
                            'weekday': the_day.strftime("%A"),
                            'sun': {
                                'event': [
                                    {'type': 'rise', 'time': time.fromisoformat(day.get("sunrise", None))},
                                    {'type': 'set', 'time': time.fromisoformat(day.get("sunset", None))},
                                ],
                            },
                            'moon': {
                                'event': [
                                    *([{'type': 'rise', 'time': time.fromisoformat(day["moonrise"])}] if day.get("moonrise", None) is not None else []),
                                    *([{'type': 'set', 'time': time.fromisoformat(day["moonset"])}] if day.get("moonset", None) is not None else []),
                                ],
                                'phase': day.get("moonphase", None),
                            },
                        }
                        astro_data.append(astro_day)
                    return astro_data
                else:
                    raise Exception(f"Error fetching astro data: {response.status}")

    async def run(self) -> None:
        logger.info(f"URL: {self.url}")
        try:
            while not self.exit:
                try:
                    astro_data = await self.get_data(date.today())
                    astro_data_json = json_serial(astro_data)

                    logger.info(astro_data_json)
                    self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "astro"), astro_data_json, retain=True)

                    now = datetime.now()
                    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    secs = (tomorrow - now).total_seconds()
                    logger.info(f"Next update in {secs} seconds at {tomorrow.isoformat()}")
                    await asyncio.sleep(secs)

                except Exception as e:
                    logger.error(f"Error: {e}")
        except KeyboardInterrupt:
            logger.info("Exit...")

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())
        loop.close()
