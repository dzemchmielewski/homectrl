import json
import logging
import datetime
import re
import aiohttp

from backend.services.meteoproviders.provider import MeteoProvider

logger = logging.getLogger("onair.imgw")

iconmap = {
    "n0z00d": "sun",
    "n0z10d": "sun-fog",
    "n0z50d": "cloud-sun-rain",
    "n0z60d": "cloud-sun-rain",
    "n0z70d": "cloud-sun-snow",
    "n0z80d": "cloud-sun-rain",
    "n0z90d": "thunderstorm-sun",

    "n1z00d": "sun",
    "n1z10d": "sun-fog",
    "n1z50d": "cloud-sun-rain",
    "n1z60d": "cloud-sun-rain",
    "n1z70d": "cloud-sun-snow",
    "n1z80d": "cloud-sun-rain",
    "n1z90d": "thunderstorm-sun",

    "n2z00d": "cloud-sun",
    "n2z10d": "cloud-sun",
    "n2z50d": "cloud-sun-rain",
    "n2z60d": "cloud-sun-rain",
    "n2z70d": "cloud-sun-snow",
    "n2z80d": "cloud-sun-rain",
    "n2z90d": "thunderstorm-sun",

    "n3z00d": "cloud-sun",
    "n3z10d": "cloud-sun-fog",
    "n3z50d": "cloud-sun-rain",
    "n3z60d": "cloud-sun-rain",
    "n3z70d": "cloud-sun-snow",
    "n3z80d": "cloud-sun-rain",
    "n3z90d": "thunderstorm-sun",
    "n3z00d": "cloud-sun",

    "n4z00d": "cloud-sun",
    "n4z10d": "cloud-sun-fog",
    "n4z50d": "cloud-sun-rain",
    "n4z60d": "cloud-sun-rain",
    "n4z70d": "cloud-sun-snow",
    "n4z80d": "cloud-sun-rain",
    "n4z90d": "thunderstorm-sun",
    "n4z00d": "cloud-sun",

    "n5z00d": "cloud-sun",
    "n5z10d": "cloud-sun-fog",
    "n5z50d": "cloud-sun-rain",
    "n5z60d": "cloud-sun-rain",
    "n5z70d": "cloud-sun-snow",
    "n5z80d": "cloud-sun-rain",
    "n5z90d": "cloud-snow",

    "n6z00d": "cloud",
    "n6z10d": "fog",
    "n6z50d": "cloud-rain",
    "n6z60d": "cloud-rain",
    "n6z70d": "cloud-sleet",
    "n6z80d": "cloud-rain",
    "n6z90d": "cloud-snow",

    "n7z00d": "cloud",
    "n7z10d": "fog",
    "n7z50d": "cloud-rain",
    "n7z60d": "cloud-rain",
    "n7z70d": "cloud-snow",
    "n7z80d": "cloud-rain",
    "n7z90d": "cloud-snow",

    "n8z00d": "cloud",
    "n8z10d": "fog",
    "n8z50d": "cloud-rain",
    "n8z60d": "cloud-rain",
    "n8z70d": "cloud-snow",
    "n8z80d": "cloud-rain",
    "n8z90d": "cloud-snow",

    "n0z00n": "moon",
    "n0z10n": "moon-fog",
    "n0z50n": "cloud-moon-rain",
    "n0z60n": "cloud-moon-rain",
    "n0z70n": "cloud-moon-snow",
    "n0z80n": "cloud-moon-rain",
    "n0z90n": "thunderstorm-moon",

    "n1z00n": "moon",
    "n1z10n": "moon-fog",
    "n1z50n": "cloud-moon-rain",
    "n1z60n": "cloud-moon-rain",
    "n1z70n": "cloud-moon-snow",
    "n1z80n": "cloud-moon-rain",
    "n1z90n": "thunderstorm-moon",

    "n2z00n": "moon",
    "n2z10n": "moon-fog",
    "n2z50n": "cloud-moon-rain",
    "n2z60n": "cloud-moon-rain",
    "n2z70n": "cloud-moon-snow",
    "n2z80n": "cloud-moon-rain",
    "n2z90n": "thunderstorm-moon",

    "n3z00n": "cloud-moon",
    "n3z10n": "cloud-moon-fog",
    "n3z50n": "cloud-moon-rain",
    "n3z60n": "cloud-moon-rain",
    "n3z70n": "cloud-moon-snow",
    "n3z80n": "cloud-moon-rain",
    "n3z90n": "thunderstorm-moon",

    "n4z00n": "cloud-moon",
    "n4z10n": "cloud-moon-fog",
    "n4z50n": "cloud-moon-rain",
    "n4z60n": "cloud-moon-rain",
    "n4z70n": "cloud-moon-snow",
    "n4z80n": "cloud-moon-rain",
    "n4z90n": "thunderstorm-moon",

    "n5z00n": "cloud-moon",
    "n5z10n": "cloud-moon-fog",
    "n5z50n": "cloud-moon-rain",
    "n5z60n": "cloud-moon-rain",
    "n5z70n": "cloud-moon-snow",
    "n5z80n": "cloud-moon-rain",
    "n5z90n": "cloud-snow",

    "n6z00n": "cloud",
    "n6z10n": "fog",
    "n6z50n": "cloud-rain",
    "n6z60n": "cloud-rain",
    "n6z70n": "cloud-sleet",
    "n6z80n": "cloud-rain",
    "n6z90n": "cloud-snow",

    "n7z00n": "cloud",
    "n7z10n": "fog",
    "n7z50n": "cloud-rain",
    "n7z60n": "cloud-rain",
    "n7z70n": "cloud-snow",
    "n7z80n": "cloud-rain",
    "n7z90n": "cloud-snow",

    "n8z00n": "cloud",
    "n8z10n": "fog",
    "n8z50n": "cloud-rain",
    "n8z60n": "cloud-rain",
    "n8z70n": "cloud-snow",
    "n8z80n": "cloud-rain",
    "n8z90n": "cloud-snow",
}


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
        icon = iconmap[
            cond['Icon'] if 'Icon' in cond else (cond['Icon10'] if 'Icon10' in cond else None)]
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
            'icon': icon,
            'date': datetime.datetime.fromisoformat(cond['Date']).astimezone(),
            'create_at': datetime.datetime.now(),
            'source': self.name,
        }

    async def forecast(self) -> dict:
        data = (await self.data())['data']['Data']
        data = [i for i in data if i['Type'] == 'Type_Hour']
        # if logger.level == logging.DEBUG:
        #     with open("imgw.json", "w") as f:
        #         json.dump(data, f, indent=2)
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
            'irradiance_radiation': [round(float(value['Irradiance_Radiation']), 1) for value in data],
            'icon': [iconmap[value['Icon']] for value in data],
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
