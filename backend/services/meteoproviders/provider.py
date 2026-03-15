import datetime


class MeteoProvider:

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

    def C_to_K(C: float) -> float:
        return round(C + 273.15, 1)

    def meteo(self) -> dict:
        raise NotImplementedError("This method should be overridden by subclasses")

    def history(self) -> dict:
        raise NotImplementedError("This method should be overridden by subclasses")

    def forecast_hours(self) -> dict:
        raise NotImplementedError("This method should be overridden by subclasses")

if __name__ == "__main__":
    import backend.tools as tools
    provider = MeteoProvider()
    print(tools.json_serial(provider.forecast(), indent=2))