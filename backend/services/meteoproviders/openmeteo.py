import datetime

import aiohttp
import logging

from backend.services.meteoproviders.provider import MeteoProvider

logger = logging.getLogger("onair.openmeteo")

class OpenMeteoProvider(MeteoProvider):

    def __init__(self, latitude: float, longitude: float):
        self.weather_url = ("https://api.open-meteo.com/v1/forecast"
                            f"?latitude={latitude}&longitude={longitude}"
                            # "&current_weather=true"
                            "&current="
                            "pressure_msl,surface_pressure,temperature_2m,relative_humidity_2m,"
                            "precipitation,showers,rain,snowfall,weather_code,"
                            "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
                            "&wind_speed_unit=ms"
                            "&timezone=Europe%2FBerlin&forecast_days=0&format=json")

    async def get_weather(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.weather_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(await response.text())
                    return {
                        'temperature': round(float(data['current']['temperature_2m']), 1),
                        'humidity': round(float(data['current']['relative_humidity_2m']), 1),
                        'pressure': {
                            'real': round(float(data['current']['surface_pressure']), 1),
                            'sea_level': None,
                        },
                        'precipitation': round(float(data['current']['precipitation']), 1),
                        'wind': {
                            'speed': round(float(data['current']['wind_speed_10m']), 1),
                            'direction': int(data['current']['wind_direction_10m']),
                            'direction_desc': self.desc_direction(int(data['current']['wind_direction_10m'])),
                            'max': {
                                'speed': round(float(data['current']['wind_gusts_10m']), 1),
                                'direction': None,
                                'direction_desc': None,
                            }
                        },
                        'solar_radiation': None,
                        'date': datetime.datetime.fromisoformat(data['current']['time']).astimezone(),
                        'create_at': datetime.datetime.now(),
                        'source': 'openmeteo',
                    }
                else:
                    raise Exception(f"[weather] Error fetching data: {response.status}")


if __name__ == "__main__":
    import sys, os, asyncio
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
    print("SYS: ", sys.path)

    from configuration import Configuration

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    async def main():
        provider = OpenMeteoProvider(*Configuration.location())
        weather = await provider.get_weather()
        logger.info(weather)

    asyncio.run(main())
