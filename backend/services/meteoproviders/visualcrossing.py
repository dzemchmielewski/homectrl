import datetime
import aiohttp
import logging

from backend.services.meteoproviders.provider import MeteoProvider

logger = logging.getLogger("onair.visualcrossing")

class VisualCrossingProvider(MeteoProvider):

    def __init__(self, latitude: float, longitude: float, apikey: str, *args, **kwargs):
        super().__init__("visualcrossing")
        self.weather_url = (
            "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
            f"{latitude}, {longitude}?"
            "unitGroup=metric"
            "&include=current,alerts"
            f"&key={apikey}"
            "&contentType=json")

    async def current(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.weather_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(await response.text())
                    cond = data['currentConditions']

                    return {
                        'temperature': round(float(cond['temp']), 1),
                        'humidity': round(float(cond['humidity']), 1),
                        'pressure': {
                            'real': round(float(cond['pressure']), 1),
                            'sea_level': None,
                        },
                        'precipitation': round(float(cond['precip'] if cond['precip'] else 0), 1),
                        'wind': {
                            'speed': self.kmh_to_ms(cond['windspeed']),
                            'direction': int(cond['winddir']),
                            'direction_desc': self.desc_direction(int(cond['winddir'])),
                            'max': {
                                'speed': round(float(cond['windgust']), 1) if cond['windgust'] else None,
                                'direction': None,
                                'direction_desc': None,
                            }
                        },
                        'solar_radiation': int(cond['solarradiation']),
                        'date': datetime.datetime.fromisoformat(
                            data['days'][0]['datetime'] + " " + cond['datetime']
                        ).astimezone(),
                        'create_at': datetime.datetime.now(),
                        'source': self.name,
                    }
                else:
                    raise Exception(f"[weather] Error fetching data: {response.status}")


if __name__ == "__main__":
    import asyncio
    from configuration import Configuration

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    async def main():
        provider = VisualCrossingProvider(
            Configuration.get('visualcrossing')['api_key'],
            53.021642188040666, 18.567522923394737)
        weather = await provider.meteo()
        logger.info(weather)

    asyncio.run(main())
