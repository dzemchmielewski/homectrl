import logging
import aiohttp
from backend.services.meteoproviders.provider import MeteoProvider, MeteoForecastProvider

logger = logging.getLogger("onair.icm")

class ICMProvider(MeteoProvider):

    def __init__(self, latitude: float, longitude: float, *args, **kwargs):
        super().__init__("icm")
        self.available_url = "https://devmgramapi.meteo.pl/meteorograms/available"
        self.um4_60_url = "https://devmgramapi.meteo.pl/meteorograms/um4_60"
        self.post = {"date":0,"point":{"lat":latitude,"lon":longitude}}

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

    async def forecast(self) -> dict:
        data = await self.data()
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

if __name__ == "__main__":
    import asyncio
    from configuration import Configuration

    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

    async def main(provider: MeteoForecastProvider):
        frct = await provider.forecast()
        logger.info(frct)

    provider = ICMProvider(*Configuration.location())
    asyncio.run(main(provider))
