import asyncio
from datetime import date, time, datetime, timedelta

import aiohttp
import logging

from backend.services.onairservice import OnAirService
from configuration import Topic, Configuration
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.astro")

class Astro(OnAirService):

    days_before_today = 1
    days_after_today = 5

    phase_events = [
        (0.0, 'new_moon'),
        (0.25, '1st_quarter'),
        (0.5, 'full_moon'),
        (0.75, '4th_quarter'),
        (1.0, 'new_moon'),
    ]
    phase_event_tolerance = 0.03

    def __init__(self):
        super().__init__()
        self.url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/Toru%C5%84"
        self.token = Configuration.get("visualcrossing").get("api_key")
        self.exit = False

    async def get_data(self, day: date) -> dict:
        logger.debug(f"Fetching astro data for day: {day}")
        d_from = (day - timedelta(days=self.days_before_today)).strftime("%Y-%m-%d")
        d_to = (day + timedelta(days=self.days_after_today)).strftime("%Y-%m-%d")
        logger.info("Fetching astro for date range: " + d_from + " - " + d_to)
        url = (self.url
               + "/" + d_from + "/" + d_to
               + "?unitGroup=metric&key=" + self.token
               + "&contentType=json&elements=datetime,moonphase,sunrise,sunset,moonrise,moonset")

        logger.debug(f"url: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                logger.debug(f"Response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.debug(await response.text())

                    astro_data = []
                    for astro_day in data["days"]:
                        astro_day_date = datetime.strptime(astro_day["datetime"], "%Y-%m-%d").date()
                        logger.debug(f"Processing astro data for date: {astro_day_date}")

                        moon_events = []
                        if astro_day.get("moonrise", None) is not None:
                            moon_events.append({'type': 'rise', 'time': time.fromisoformat(astro_day["moonrise"])})
                        if astro_day.get("moonset", None) is not None:
                            moon_events.append({'type': 'set', 'time': time.fromisoformat(astro_day["moonset"])})

                        moon_events.sort(key=lambda e: e['time'])

                        day_record = {
                            'day': {
                                'date': astro_day_date,
                                'weekday': astro_day_date.strftime("%A"),
                                'day_offset': (astro_day_date - day).days,
                            },
                            'sun': {
                                'events': [
                                    {'type': 'rise', 'time': time.fromisoformat(astro_day.get("sunrise", None))},
                                    {'type': 'set', 'time': time.fromisoformat(astro_day.get("sunset", None))},
                                ],
                            },
                            'moon': {
                                'events': moon_events,
                                'phase': astro_day.get("moonphase", None),
                            },
                        }
                        astro_data.append(day_record)


                    # just incase sort by date
                    astro_data.sort(key=lambda d: d['day']['date'])

                    return {
                        'name': 'astro',
                        'astro': astro_data,
                    }
                else:
                    raise Exception(f"Error fetching astro data: {response.status}")

    @staticmethod
    async def _add_datetime(astro_data: dict) -> dict:
        astro_data['datetime'] = {
            'date': date.today(),
            'time': datetime.now().time(),
            'weekday': datetime.now().strftime("%A"),
        }
        return astro_data

    async def _add_moon_phase_events(self, astro_data: dict) -> dict:
        for value, name in self.phase_events:
            min_diff = float('inf')
            event_day = None
            for day in astro_data['astro']:
                phase = day['moon']['phase']
                diff = abs(phase - value)
                if diff < min_diff and diff <= self.phase_event_tolerance:
                    min_diff = diff
                    event_day = day
            if event_day:
                events = event_day['moon'].setdefault('events', [])
                events.append({'type': 'phase', 'name': name})
        return astro_data

    async def astro(self) -> None:
        logger.info(f"URL: {self.url}")
        done = False
        while not done:
            try:
                astro_data = await self.get_data(date.today())
                astro_data = await self._add_datetime(astro_data)
                astro_data = await self._add_moon_phase_events(astro_data)
                logger.debug(f"{astro_data}")

                astro_data_json = json_serial(astro_data)
                logger.info(astro_data_json)
                self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "astro"), astro_data_json, retain=True)
                done = True
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour before retrying

    async def run(self) -> None:
        scheduler = AsyncIOScheduler()

        # every day at midnight
        scheduler.add_job(self.astro, CronTrigger.from_crontab("1 0 * * *"))

        # run once at startup:
        scheduler.add_job(self.astro)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()
