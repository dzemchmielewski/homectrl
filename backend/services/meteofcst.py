import aiohttp
import logging
import json
import os

logger = logging.getLogger("onair.meteofcst")

class MeteoForcast:

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

    async def transform(self, data: dict) -> dict:
        return {
            'name': 'meteofcst',
            'meteofcst': {
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
        }


    async def lauch(self) -> None:
        script_path = os.path.abspath(__file__)

        load_new = True

        if load_new:
            meteo_data = await self.data()
            with open(os.path.join(os.path.dirname(script_path), 'meteofcst_meteopl.json'), 'w') as f:
                json.dump(meteo_data, f, indent=4)
            logger.info("Meteo forecast data saved to meteofcst_meteopl.json")
        else:
            with open(os.path.join(os.path.dirname(script_path), 'meteofcst_meteopl.json'), 'r') as f:
                meteo_data = json.load(f)
            logger.info("Meteo forecast data loaded from meteofcst_meteopl.json")

        transformed_data = await self.transform(meteo_data)
        with open(os.path.join(os.path.dirname(script_path), 'meteofcst.json'), 'w') as f:
            json.dump(transformed_data, f, indent=4)

        logger.info("Transformed meteo forecast data saved to meteofcst.json")
        logger.info(f"{json.dumps(transformed_data)}")