class MeteoProvider:

    @staticmethod
    def desc_direction(degree: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degree / 45) % 8
        return directions[idx]

    def get_weather(self) -> dict:
        raise NotImplementedError("This method should be overridden by subclasses")
