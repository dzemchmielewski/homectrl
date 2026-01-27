import asyncio
import json
import os
from datetime import date

import logging

from backend.services.onairservice import OnAirService
from configuration import Topic
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.holidays")


class Holidays(OnAirService):

    def __init__(self):
        super().__init__()
        self.holidays = json.load(open(os.path.join(os.path.dirname(__file__), 'holidays-2026.json')))


    async def dojob(self) -> None:
        done = False
        while not done:
            try:
                today = date.today()
                result = {
                    'name': 'holidays',
                    'date': today,
                    'holidays': self.holidays[str(today.month)][str(today.day)],
                }
                logger.debug(f"{result}")
                result_json = json_serial(result)
                logger.info(result_json)
                self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "holidays"), result_json, retain=True)
                done = True
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour before retrying

    async def run(self) -> None:
        scheduler = AsyncIOScheduler()

        # every day at midnight
        scheduler.add_job(self.dojob, CronTrigger.from_crontab("1 0 * * *"))
        # run once at startup:
        scheduler.add_job(self.dojob)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()
