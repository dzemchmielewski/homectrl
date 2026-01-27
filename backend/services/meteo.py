import asyncio
import datetime
import aiohttp
import logging

from backend.services.meteoproviders.openmeteo import OpenMeteoProvider
from backend.services.meteoproviders.umk import UMKProvider
from backend.services.onairservice import OnAirService, noexception
from configuration import Topic, Configuration
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.meteo")

logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)


class Meteo(OnAirService):

    def __init__(self):
        super().__init__()
        self.data_url = "https://pogoda.umk.pl/api/last?type="
        self.exit = False
        self.providers = [UMKProvider(), OpenMeteoProvider(*Configuration.location())]

    @staticmethod
    def desc_direction(degree: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degree / 45) % 8
        return directions[idx]

    async def _data(self, name: str, data_type: str) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.data_url + data_type) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    if isinstance(json_resp, dict):
                        logger.debug(f"[{name}] {await response.text()}")
                        data = json_serial({
                            'time': datetime.datetime.fromtimestamp(json_resp['data'][0]['date']),
                            'values': [item['value'] for item in json_resp['data']],
                        })
                        logger.debug(f"[{name}] Data: {data}")
                        self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo/" + name), data, retain=True)
                    else:
                            raise Exception(f"[{name}] Unexpected response format: expected dict, got {type(json_resp)}")
                else:
                    raise Exception(f"[{name}] Error fetching data: {response.status}")

    @noexception(logger=logger)
    async def meteo(self) -> None:
        weather = None
        for provider in self.providers:
            try:
                weather = await provider.get_weather()
                if weather:
                    break
            except Exception as e:
                logger.error(f"Error fetching weather from {provider.__class__.__name__}: {e}")

        if weather:
            message = json_serial(weather)
            logger.debug(message)
            self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo"), message, retain=True)
        else:
            logger.error("All providers failed to fetch weather data.")

    @noexception(logger=logger)
    async def temperature(self) -> None:
        return await self._data('temperature', 'tempAir200')
    @noexception(logger=logger)
    async def precipitation(self) -> None:
        return await self._data('precipitation', 'precipitation1')
    @noexception(logger=logger)
    async def pressure(self) -> None:
        return await self._data('pressure', 'atmosphericPressureSL')


    async def run(self) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.meteo, CronTrigger.from_crontab("*/5 * * * *"))  # every 5 minutes

        every_hour_trigger = CronTrigger.from_crontab("4 * * * *")  # every hour at minute 4
        scheduler.add_job(self.temperature, every_hour_trigger)
        scheduler.add_job(self.precipitation, every_hour_trigger)
        scheduler.add_job(self.pressure, every_hour_trigger)

        # run once at startup:
        scheduler.add_job(self.meteo)
        scheduler.add_job(self.temperature)
        scheduler.add_job(self.precipitation)
        scheduler.add_job(self.pressure)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()





