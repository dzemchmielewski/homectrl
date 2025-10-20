import datetime
import time
import logging
from backend.services.onairservice import OnAirService
from collections import deque
import human_readable as hr

from backend.sms import SMS
from backend.storage import Laundry, model_to_dict, device_entities
from backend.tools import json_serial, json_deserial
from configuration import Topic


logger = logging.getLogger("onair.laundry")

class LaundryOnAir(OnAirService):

    INPUT_TOPIC = Topic.OnAir.format("electricity", "bathroom")
    OUTPUT_TOPIC = Topic.OnAir.format(Topic.OnAir.Facet.activity, "laundry")

    def __init__(self):
        super().__init__()
        self.sms = SMS()
        self.active_laundry = None
        self.laundry = None
        self.active_power_queue = deque((), 2)
        self.floating_start_time = None
        self.start_parameters = None

    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.info("Laundry service connected to MQTT broker.")
        client.subscribe(LaundryOnAir.INPUT_TOPIC)
        self.laundry = Laundry.get_last()
        if self.laundry is None:
            self.laundry = Laundry()
        self.publish()

    def threshold_crossed(self):
        l = list(self.active_power_queue)
        return (sum(l)/len(l)) >= 3

    def on_message(self, client, userdata, msg):
        msg_dec = msg.payload.decode()
        logger.debug("[{}]{}".format(msg.topic, msg_dec))
        data = json_deserial(msg_dec)
        if msg.topic == self.INPUT_TOPIC:
            self.active_power_queue.append(data["active_power"])

            active = self.laundry.is_active()
            new_active = self.threshold_crossed()

            if active and not new_active:
                # Laundry has ended
                active = False

            elif active == new_active:
                self.floating_start_time = None

            elif not active and new_active:
                # Probably laundry is starting

                if self.floating_start_time is None:
                    # Start floating time
                    self.floating_start_time = time.time()
                    self.start_parameters = data

                else:
                    if time.time() - self.floating_start_time > 30:
                        # if floating time has passed, laundry is started
                        active = True
                        self.floating_start_time = None

            if not self.laundry.is_active() and active:
                # Laundry has started!
                self.laundry = Laundry(start_at=datetime.datetime.fromisoformat(self.start_parameters["create_at"]),
                                       start_energy=self.start_parameters["active_energy"])
                self.laundry.save(force_insert=True)
                self.publish()
            elif self.laundry.is_active() and not active:
                # Laundry has finished!
                self.laundry.end_at = datetime.datetime.fromisoformat(data["create_at"])
                self.laundry.end_energy = data["active_energy"]
                self.laundry.save()
                self.publish()
                self.sms.laundry()

    def publish(self):
        output = model_to_dict(self.laundry)
        output["name"] = "laundry"
        output["is_active"] = self.laundry.is_active()
        if not self.laundry.is_active():
            output["duration"] = hr.precise_delta(self.laundry.end_at - self.laundry.start_at, formatting=".0f")
            output["energy"] = (self.laundry.end_energy - self.laundry.start_energy) / 1000

        message = json_serial(output)
        logger.info("PUBLISH {} -> {}".format(self.OUTPUT_TOPIC, message))
        self.mqtt.publish(self.OUTPUT_TOPIC, message, retain=True)


