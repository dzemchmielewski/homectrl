import datetime

import aiohttp
import logging

from backend.services.meteoproviders.provider import MeteoProvider
from backend.tools import json_serial
from configuration import Topic

logger = logging.getLogger("onair.umk")

class UMKProvider(MeteoProvider):

    def __init__(self, *args, **kwargs):
        self.weather_url = "https://pogoda.umk.pl/api/weather"
        self.data_url = "https://pogoda.umk.pl/api/last?type="

    async def meteo(self) -> dict:
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
                        datereceived = datetime.datetime.fromisoformat(json_resp['dateUTC']).astimezone()

                        # throws error if the date is older then 20 minutes:
                        if (datetime.datetime.now(datetime.timezone.utc) - datereceived).total_seconds() > 20 * 60:
                            raise Exception(f"[weather] UMK data is outdated: received at {datereceived.isoformat()}")

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
                            'source': 'umk',
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
                        return {
                            'time': datetime.datetime.fromtimestamp(json_resp['data'][0]['date']),
                            'values': [item['value'] for item in json_resp['data']],
                        }
                    else:
                        raise Exception(f"[{name}] Unexpected response format: expected dict, got {type(json_resp)}")
                else:
                    raise Exception(f"[{name}] Error fetching data: {response.status}")

    async def history(self) -> None:
        return {
            'temperature': await self._data('temperature', 'tempAir200'),
            'precipitation': await self._data('precipitation', 'precipitation1'),
            'pressure': await self._data('pressure', 'atmosphericPressureSL'),
        }
