import asyncio
import datetime
import logging

from backend.services.meteoproviders.icm import ICMProvider
from backend.services.meteoproviders.imgw import IMGWProvider
from backend.services.meteoproviders.openmeteo import OpenMeteoProvider
from backend.services.meteoproviders.umk import UMKProvider
from backend.services.meteoproviders.visualcrossing import VisualCrossingProvider
from backend.services.onairservice import OnAirService, noexception
from configuration import Topic, Configuration
from backend.tools import json_serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("onair.meteo")

logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)


class Meteo(OnAirService):

    def __init__(self):
        super().__init__()
        self.exit = False
        self.providers = [
            UMKProvider(),
            OpenMeteoProvider(*Configuration.location()),
            IMGWProvider(*Configuration.location()),
            ICMProvider(*Configuration.location()),
            VisualCrossingProvider(*Configuration.location(), Configuration.MAP['visualcrossing']['api_key'])]

    @noexception(logger=logger)
    async def _meteo(self, type: str, get_meteo_callback):
        first_meteo = None
        logger.debug(f"Fetching meteo {type}")
        for name in Configuration.meteo_providers()[type]:
            message = None
            try:
                logger.debug(f"Fetching meteo {type} from provider {name}")
                provider = [p for p in self.providers if p.name == name][0]
                weather = await get_meteo_callback(provider)
                if not weather:
                    raise Exception(f"Empty response when fetching meteo {type} from provider {provider.name}")
                message = json_serial({
                    'source': name,
                    'error': None,
                    'create_at': datetime.datetime.now(),
                    'data': weather,
                    })
                if first_meteo is None:
                    first_meteo = message
            except Exception as e:
                logger.error(f"Error fetching meteo {type} from provider {provider.name}: {e}")
                message - json_serial({
                    "error": f"{e}",
                    "source": provider.name,
                    "create_at": datetime.datetime.now(),
                })
            if message:
                logger.debug(message)
                self.mqtt.publish(
                    Topic.OnAir.format(Topic.OnAir.Facet.meteo, f"{type}/{provider.name}"),
                    message, retain=True)
        if first_meteo:
            self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.meteo, f"{type}"), first_meteo, retain=True)

    @noexception(logger=logger)
    async def current(self) -> None:
        async def callback(provider):
            return await provider.current()
        await self._meteo('current', callback)

    @noexception(logger=logger)
    async def past(self) -> None:
        async def callback(provider):
            return await provider.past()
        await self._meteo('past/hourly', callback)

    @noexception(logger=logger)
    async def forecast(self) -> None:
        async def callback(provider):
            return await provider.forecast()
        await self._meteo('forecast/hourly', callback)

    async def run(self) -> None:
        scheduler = AsyncIOScheduler()

        every_five_min_trigger = CronTrigger.from_crontab("*/5 * * * *")  # every 5 minutes
        scheduler.add_job(self.current, every_five_min_trigger)

        every_hour_trigger = CronTrigger.from_crontab("4 * * * *")  # every hour at minute 4
        scheduler.add_job(self.past, every_hour_trigger)
        scheduler.add_job(self.forecast, every_hour_trigger)

        # run once at startup:
        scheduler.add_job(self.current)
        scheduler.add_job(self.past)
        scheduler.add_job(self.forecast)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()
