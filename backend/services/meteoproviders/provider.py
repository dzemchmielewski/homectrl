from typing import Protocol


class MeteoProvider:
    def __init__(self, name):
        self.name = name

    @staticmethod
    def desc_direction(degree: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degree / 45) % 8
        return directions[idx]

    @staticmethod
    def kmh_to_ms(kmh: float) -> float:
        return round(kmh / 3.6, 1)

    @staticmethod
    def K_to_C(K: float) -> float:
        return round(K - 273.15, 1)

    @staticmethod
    def C_to_K(C: float) -> float:
        return round(C + 273.15, 1)


class MeteoForecastProvider(Protocol):
    name: str
    async def forecast(self) -> dict: ...

class MeteoCurrentProvider(Protocol):
    name: str
    async def current(self) -> dict: ...

class MeteoPastProvider(Protocol):
    name: str
    async def past(self) -> dict: ...



# Since 3.12...
# class MeteoResponse[T](TypedDict):
#     source: str
#     error: NotRequired[str | None]
#     create_at: datetime.datetime
#     data: T
#
# class MeteoForecastResponse(TypedDict):
#     time: str
#     temperature: ForecastTemperatureResponse
#     humidity: list[float]
#     pressure: list[float]
#     wind_speed: list[float]
#     wind_direction: list[int]
#     precipitation: ForecastPrecipitationResponse
#
#
# ForecastTemperatureResponse = TypedDict(
#     "ForecastTemperatureResponse",
#     {"air": list[float], "apparent": list[float]})
# ForecastPrecipitationResponse = TypedDict(
#     "ForecastPrecipitationResponse",
#     {'average': list[float], 'probability': list[float], 'type': list})
