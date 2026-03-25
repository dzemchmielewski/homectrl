import datetime
import re

import aiohttp
import logging

from backend.services.meteoproviders.provider import MeteoProvider

logger = logging.getLogger("onair.imgw")

class IMGWProvider(MeteoProvider):

    def __init__(self, latitude: float, longitude: float, *args, **kwargs):
        super().__init__("imgw")
        self.latitude = latitude
        self.longitude = longitude
        self.recent_data = None

    async def current(self):
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
                        cond = self.recent_data['data']['Data'][0]
                        logger.debug(await response.text())
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
                    else:
                        raise Exception(f"[weather] Error fetching data: {response.status}")
            else:
                raise Exception("[weather] Error fetching API token from IMGW")


if __name__ == "__main__":
    import asyncio
    from configuration import Configuration

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    async def main():
        provider = IMGWProvider(*Configuration.location())
        weather = await provider.meteo()
        logger.info(weather)
        with (open("imgw.json", "w") as f):
            import json
            json.dump(provider.recent_data, f, default=str, indent=2)

    asyncio.run(main())
