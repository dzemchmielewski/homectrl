import asyncio
import datetime
import logging

from peewee import DecimalField, DateTimeField, CharField

from backend.services.meteoproviders.imgw import IMGWProvider
from backend.services.meteoproviders.openmeteo import OpenMeteoProvider
from backend.services.meteoproviders.umk import UMKProvider
from backend.services.meteoproviders.visualcrossing import VisualCrossingProvider
from backend.services.onairservice import OnAirService, noexception
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import backend.storage as db
from configuration import Configuration

logger = logging.getLogger("onair.meteocmp")

logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)


class MeteoCompare(db.BaseModel):
    create_at = DateTimeField()
    location = CharField(max_length=15)
    provider = CharField(max_length=25)
    name = CharField(max_length=25)
    value = DecimalField(decimal_places=1)
    datetime = DateTimeField()

with db.database:
    db.database.create_tables([MeteoCompare])

# Commented out OnAirService inheritance, so the service will not launched by OnAir,
# but can be run manually for testing or one-off comparisons.
#class MeteoCmp(OnAirService):
class MeteoCmp:

    LOCATION = {
        'torun': Configuration.locations()['umk'],
        'zamek': Configuration.locations()['zamek_bierzglowski'],
    }
    PROVIDER  = {
        'openmeteo': OpenMeteoProvider,
        'visualcrossing': VisualCrossingProvider,
        'imgw': IMGWProvider,
    }

    def __init__(self):
        super().__init__()
        self.exit = False

    @staticmethod
    def desc_direction(degree: int) -> str:
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(degree / 45) % 8
        return directions[idx]

    @noexception(logger=logger)
    async def meteocmp(self) -> None:
        now = datetime.datetime.now()
        try:
            for location in self.LOCATION.keys():
                for provider in self.PROVIDER.keys():
                    logger.debug(f"Fetching weather from {provider} for {location}...")
                    weather = await self.PROVIDER[provider](*self.LOCATION[location], Configuration.get('visualcrossing')['api_key']).meteo()
                    MeteoCompare.create(
                        create_at=now,
                        location=location,
                        provider=provider,
                        name='temperature',
                        value=weather['temperature'],
                        datetime = weather['date'],
                    )
            weather = await UMKProvider().meteo()
            MeteoCompare.create(
                create_at=now,
                location='torun',
                provider='umk',
                name='temperature',
                value=weather['temperature'],
                datetime = weather['date'],
            )

        except Exception as e:
            logger.error(f"Error in meteocmp: {e}")


    async def run(self) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.meteocmp, CronTrigger.from_crontab("*/5 * * * *"))  # every 5 minutes

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()

if __name__ == "__main__":
    service = MeteoCmp()
    try:
        asyncio.run(service.meteocmp())
    except KeyboardInterrupt:
        service.exit = True
