import asyncio
import datetime
import aiohttp
import logging

from backend.services.onairservice import OnAirService, noexception
from configuration import Topic
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.meteo")

logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)

class Meteo(OnAirService):


    def __init__(self):
        super().__init__()
        self.weather_url = "https://pogoda.umk.pl/api/weather"
        self.data_url = "https://pogoda.umk.pl/api/last?type="
        self.exit = False

    @staticmethod
    def desc_direction(degree: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degree / 45) % 8
        return directions[idx]


    async def _get_weather(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.weather_url) as response:
                if response.status == 200:
                    json_resp = await response.json()
                    # Debugging error: list indices must be integers or slices, not str
                    # now = datetime.datetime.now()
                    # if now.hour == 1:
                    #     logger.info(f"Full response: {json_resp}")
                    if isinstance(json_resp, dict):
                        logger.debug(await response.text())
                        data = json_resp['data']
                        return {
                            'temperature': round(float(data['tempAir200']['value']), 1),
                            'humidity': round(float(data['airHumidity']['value']), 1),
                            'pressure': {
                                'real': round(float(data['atmosphericPressure']['value']), 1),
                                'sea_level': round(float(data['atmosphericPressureSL']['value']), 1),
                            },
                            'precipitation': round(float(data['precipitation1']['value']), 1),
                            'wind': {
                                'speed': round(float(data['windSpeed']['value']), 1),
                                'direction': int(data['windDegree']['value']),
                                'direction_desc': self.desc_direction(int(data['windDegree']['value'])),
                                'max': {
                                    'speed': round(float(data['maxWindSpeed10']['value']), 1),
                                    'direction': int(data['maxWindDegree10']['value']),
                                    'direction_desc': self.desc_direction(int(data['maxWindDegree10']['value'])),
                                }
                            },
                            'solar_radiation': round(float(data['totalSolarRadiation']['value']), 1),
                            'date': datetime.datetime.fromisoformat(json_resp['dateUTC']).astimezone(),
                            'create_at': datetime.datetime.now(),
                        }
                    else:
                        raise Exception(f"[weather] Unexpected response format: expected dict, got {type(json_resp)}")
                else:
                    raise Exception(f"[weather] Error fetching data: {response.status}")

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
        weather = await self._get_weather()
        message = json_serial(weather)
        logger.debug(message)
        self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo"), message, retain=True)

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

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()





