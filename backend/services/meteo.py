import asyncio
import logging

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
            VisualCrossingProvider(*Configuration.location(), Configuration.MAP['visualcrossing']['api_key'])]

    @noexception(logger=logger)
    async def meteo(self) -> None:
        first_meteo = None
        for provider_name in Configuration.meteo_providers():
            message = None
            try:
                provider = [p for p in self.providers if p.name == provider_name][0]
                weather = await provider.meteo()
                if not weather:
                    raise Exception(f"Empty response")
                message = json_serial(weather)
                if first_meteo is None:
                    first_meteo = message
            except Exception as e:
                logger.error(f"Error fetching meteo from provider {provider.name}: {e}")
                message - json_serial({
                    "error": f"{e}",
                    "source": provider.name
                })
            if message:
                logger.debug(message)
                self.mqtt.publish(
                    Topic.OnAir.format(Topic.OnAir.Facet.activity, f"meteo/{provider.name}"),
                    message, retain=True)
        if first_meteo:
            self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo"), first_meteo, retain=True)


    @noexception(logger=logger)
    async def history(self) -> None:
        history = None
        for provider in self.providers:
            try:
                history = await provider.history()
                if history:
                    break
            except Exception as e:
                logger.error(f"Error fetching weather from {provider.__class__.__name__}: {e}")

        if history:
            message = json_serial(history)
            logger.debug(message)
            self.mqtt.publish(Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo/history"), message, retain=True)
        else:
            logger.error("All providers failed to fetch weather data.")


    async def run(self) -> None:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.meteo, CronTrigger.from_crontab("*/5 * * * *"))  # every 5 minutes

        every_hour_trigger = CronTrigger.from_crontab("4 * * * *")  # every hour at minute 4
        scheduler.add_job(self.history, every_hour_trigger)

        # run once at startup:
        scheduler.add_job(self.meteo)
        scheduler.add_job(self.history)

        scheduler.start()
        await asyncio.Event().wait()
        scheduler.shutdown()





