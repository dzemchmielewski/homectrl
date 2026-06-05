import logging
import datetime
import re
import aiohttp

from backend.services.meteoproviders.provider import MeteoProvider

logger = logging.getLogger("onair.imgw")

class IMGWProvider(MeteoProvider):

    def __init__(self, latitude: float, longitude: float, *args, **kwargs):
        super().__init__("imgw")
        self.latitude = latitude
        self.longitude = longitude
        self.recent_data = None

    async def data(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meteo.imgw.pl/shared/web-components/serwisy-imgw/serwisy-imgw.js") as response:
                text = await response.text()
                match = re.search(r'apiToken:"([^"]+)"', text)
                api_token = match.group(1) if match else None

            if api_token:
                async with session.get("https://meteo.imgw.pl/api/v1/forecast/fcapi"
                                       f"?token={api_token}"
                                       f"&lat={self.latitude}"
                                       f"&lon={self.longitude}") as response:
                    if response.status == 200:
                        self.recent_data = await response.json()
                        logger.debug(await response.text())
                        return self.recent_data

                    else:
                        raise Exception(f"[weather] Error fetching data: {response.status}")
            else:
                raise Exception("[weather] Error fetching API token from IMGW")

    async def current(self):
        cond = (await self.data())['data']['Data'][0]
        return {
            'temperature': self.K_to_C(float(cond['Temperature'])),
            'humidity': round(float(cond['Humidity']), 1),
            'pressure': {
                'real': round(float(cond['PressureMSL']) / 100, 1),
                'sea_level': None,
            },
            'precipitation': round(float(cond['Precipitation10m']), 1),
            'wind': {
                'speed': round(float(cond['Wind_Speed']), 1),
                'direction': int(cond['Wind_Dir']),
                'direction_desc': self.desc_direction(int(cond['Wind_Dir'])),
                'max': {
                    'speed': round(float(cond['Wind_Gust']), 1),
                    'direction': None,
                    'direction_desc': None,
                }
            },
            'solar_radiation': float(cond['Irradiance_Radiation']),
            'date': datetime.datetime.fromisoformat(cond['Date']).astimezone(),
            'create_at': datetime.datetime.now(),
            'source': self.name,
        }

    async def forecast(self) -> dict:
        data = (await self.data())['data']['Data']
        data = [i for i in data if i['Type'] == 'Type_Hour']
        return {
            'time': datetime.datetime.fromisoformat(data[0]['Date']).astimezone().strftime("%Y-%m-%dT%H:%M:%S"),
            'temperature': {
                'air': [self.K_to_C(float(value['Temperature'])) for value in data],
                'apparent': [self.K_to_C(float(value['Chill'])) for value in data],
            },
            'humidity': [int(round(float(value['Humidity']), 1)) for value in data],
            'pressure': [round(float(value['PressureMSL']) / 100, 1) for value in data],
            'wind_speed': [float(value['Wind_Speed']) for value in data],
            'wind_direction': [int(value['Wind_Dir']) for value in data],
            'precipitation': {
                'average': [round(float(value['Precipitation']), 1) for value in data],
                'probability': [],
                'rain': [round(float(value['Rain']), 1) for value in data],
                'snow': [round(float(value['Snow']), 1) for value in data],
            },
        }

if __name__ == "__main__":
    import asyncio
    from configuration import Configuration

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.INFO)

    async def main():
        provider = IMGWProvider(*Configuration.location())
        result = await provider.forecast()
        from backend.tools import json_serial
        logger.info(json_serial(result))

    asyncio.run(main())
