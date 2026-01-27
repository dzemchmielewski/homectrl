import asyncio
from datetime import date

import logging

import aiohttp

from backend.services.onairservice import OnAirService
from configuration import Topic
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.meteofcst")

class MeteoForcast(OnAirService):

    def __init__(self):
        self.available_url = "https://devmgramapi.meteo.pl/meteorograms/available"
        self.um4_60_url = "https://devmgramapi.meteo.pl/meteorograms/um4_60"
        self.post = {"date":0,"point":{"lat":"53.0102721","lon":"18.6048094"}}

    async def data(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.post(self.available_url) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    logger.debug(f"{json_resp}")
                    self.post["date"] = json_resp["um4_60"][-1]
                else:
                    raise Exception(f"Error fetching available meteorograms: {response.status}")

        logger.debug(f"Fetching meteo forecast data with post: {self.post}")
        async with aiohttp.ClientSession() as session:
            async with session.post(self.um4_60_url, json=self.post) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    logger.debug(f"{await response.text()}")
                    return json_resp
                else:
                    raise Exception(f"Error fetching data: {response.status}")

    @staticmethod
    def transform(data: dict) -> dict:
        return {
                'time': data['fstart'],
                'temperature': {
                    'air': [round(value, 1) for value in data['data']['airtmp_point']['data']],
                    'apparent': [round(value, 1) for value in data['data']['dwptmp_point']['data']],
                },
                'humidity': [],
                'pressure': [],
                'wind_speed': [],
                'wind_direction': [],
                'precipitation': {
                    'average': [round(value, 1) for value in data['data']['pcpttl_aver']['data']],
                    'probability': [int(round(value, 0)) for value in data['data']['pcpttlprob_point']['data']],
                    'type': [],  # TODO
                },
            }

    async def dojob(self) -> None:
        done = False
        while not done:
            try:
                today = date.today()
                result = {
                    'name': 'meteofcst',
                    'date': today,
                    'meteofcst': self.transform(await self.data()),
                }
                logger.debug(f"{result}")
                result_json = json_serial(result)
                logger.debug(result_json)
                self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteofcst"), result_json, retain=True)
                done = True
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(5 * 60)  # Wait 5 minutes  before retrying

    async def run(self) -> None:
        scheduler = AsyncIOScheduler()
        every_hour_trigger = CronTrigger.from_crontab("4 * * * *")  # every hour at minute 4
        scheduler.add_job(self.dojob, every_hour_trigger)

        # run once at startup:
        scheduler.add_job(self.dojob)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()
