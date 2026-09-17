import asyncio
import traceback
import logging
import datetime

from backend.services.onairservice import OnAirService
from backend.tools import json_serial, json_deserial
from configuration import Topic
from backend import storage

logger = logging.getLogger("onair.devices")

class Devices(OnAirService):

    MQTT_SUBSCRIPTIONS = [
        Topic.Device.format("+", Topic.Device.Facility.live),
        Topic.Device.format("+", Topic.Device.Facility.data),
        Topic.Device.format("+", Topic.Device.Facility.capabilities),
        Topic.Device.format("+", Topic.Device.Facility.state)
    ]

    def __init__(self):
        super().__init__()
        self.start_at = datetime.datetime.now()
        self.status = {}
        self.pending_off = {}  # device_name -> asyncio.Task

    def on_message(self, client, userdata, msg):
        if Topic.Device.is_topic(msg.topic):
            try:
                logger.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
                data = json_deserial(msg.payload.decode())
                device, facility_str = Topic.Device.parse(msg.topic)
                facility = Topic.Device.Facility(facility_str)

                if facility in [Topic.Device.Facility.live, Topic.Device.Facility.data]:
                    if data.get("name") is None:
                        data["name"] = device
                    data["timestamp"] = datetime.datetime.now()

                    for entry in self.data2entries(data):
                        # process Live differently:
                        if isinstance(entry, storage.Live):
                            self.process_live_entry(entry)
                        else:
                            status_current = self.status.get(type(entry))
                            logger.debug(f"ENTRY TYPE: {type(entry)}, current status: {status_current}")
                            if status_current is not None:

                                if entry.name:
                                    current = status_current.get(entry.name)
                                    if not entry.equals(current):
                                        logger.debug("SWITCH {} for {}".format(type(entry), entry.name))
                                        self.process_entry(entry)

                    # Some additional data, passed OnAir, but not saved in the database:
                    for key, value in data.items():
                        if key.startswith("transient_"):
                            msg = {
                                "name": {"value": device},
                                "create_at": data["timestamp"],
                                "value": value
                            }
                            self.mqtt.publish(Topic.OnAir.format(key.split('_')[1], device), json_serial(msg), retain=False)

                elif facility in [Topic.Device.Facility.capabilities, Topic.Device.Facility.state]:
                    self.mqtt.publish(Topic.OnAir.format(facility, device),
                                      json_serial(data), retain=True)

                else:
                    pass
                    # logger.error("ERROR! Topic not recognized: {}".format(msg.topic))

            except UnicodeError as e:
                logger.fatal("Unicode error caught! {}".format(e))
                logger.fatal("On message: [{}]{}".format(msg.topic, msg.payload))
                traceback.print_exc()

            except Exception as e:
                logger.fatal("Exception caught! {}".format(e))
                logger.fatal("On message: [{}]{}".format(msg.topic, msg.payload.decode()))
                traceback.print_exc()
                # for line in traceback.format_stack():
                #     print(line.strip())

    @staticmethod
    def data2entries(data: dict) -> list:
        result = [storage.Live(name=data["name"], create_at=data["timestamp"], value=data.get("live") is None or data.get("live"))]
        for key, value in data.items():
            if key in ["temperature", "humidity", "darkness", "light", "presence", "pressure", "voltage", "error", "moisture", "doors", "bell", "lux"]:
                if value is not None:
                    clazz = getattr(storage, key.capitalize(), None)
                    result.append(clazz(name=data["name"], create_at=data["timestamp"], value=value))
            elif key == "radar" and value is not None:
                result.append(storage.Radar(name=data["name"], create_at=data["timestamp"],
                                    presence=value["presence"], target_state=value["target_state"],
                                    # Save for debug:
                                    move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
                                    static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
                                    # ---
                                    distance=value["distance"]))
            elif key == "radio" and value is not None:
                result.append(storage.Radio(name=data["name"], create_at=data["timestamp"],
                                    station_name=value["station"]["name"], station_code=value["station"]["code"],
                                    volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]))
            elif key == "electricity" and value is not None:
                result.append(storage.Electricity(name=data["name"], create_at=data["timestamp"],
                                          voltage=value.get('voltage'), current=value.get('current'), active_power=value.get('active_power'),
                                          active_energy=value.get('active_energy'), power_factor=value.get('power_factor')))
            elif key == "battery"and value is not None:
                result.append(storage.Battery(name=data["name"], create_at=data["timestamp"],
                                              value=value.get('value'), voltage=value.get('voltage')))
            elif key == "ceilinglight" and value is not None and isinstance(value, dict):
                result.extend([storage.Light(create_at=data["timestamp"],
                                                    name=room, value=status) for (room, status) in value.items()])
        return result

    def process_entry(self, entry: storage.HomeCtrlBaseModel, db_save=True):
        self.status[type(entry)][entry.name] = entry
        subject = Topic.OnAir.format(type(entry).__name__.lower(), entry.name)
        logger.debug("PUBLISH {} -> {}".format(subject, storage.model_to_dict(entry)))
        if db_save:
            entry.save_new_value()
        self.mqtt.publish(
            subject,
            json_serial(storage.model_to_dict(entry)),
            retain=True)

    def process_live_entry(self, entry: storage.HomeCtrlBaseModel, db_save=True):
        # logger.info(f"LIVE MSG for {entry.name}: {entry.value}")
        # if live = True
        if entry.value:
            # cancel any pending OFF when device reports it is live
            task = self.pending_off.pop(entry.name, None)
            # logger.info(f"LIVE for {entry.name} task: {task}")
            if task:
                # logger.info(f"LIVE for {entry.name} task cancel")
                task.cancel()

        # if live = False
        else:
            # schedule delayed OFF
            if entry.name not in self.pending_off:
                self.pending_off[entry.name] = asyncio.run_coroutine_threadsafe(self._delayed_off(entry), self.loop)
                # logger.info(f"LIVE for {entry.name} new task: {self.pending_off[entry.name]}")
                return  # don't process immediately - just return so far
            else:
                # the second time live = False entry -
                # - remove the delay and process it normally
                # logger.info(f"LIVE for {entry.name} pop")
                self.pending_off.pop(entry.name, None)

        status_current = self.status.get(storage.Live)
        if status_current is not None:
            if entry.name:
                current = status_current.get(entry.name)
                if not entry.equals(current):
                    logger.debug("SWITCH {} for {}".format(type(entry), entry.name))
                    self.process_entry(entry)

    async def _delayed_off(self, entry: storage.Live, delay: int = 15):
        """Delay OFF handling to avoid false LWT triggers."""
        await asyncio.sleep(delay)
        logger.info(f"Confirming OFF for {entry.name} after {delay}s delay")
        self.process_live_entry(entry)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.info(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
        for topic in self.MQTT_SUBSCRIPTIONS:
            client.subscribe(topic)
        for entity in storage.device_entities():
            self.status[entity] = {}
            for entry in entity.get_currents():
                self.process_entry(entry, False)

    def on_disconnect(self, *args, **kwargs):
        logger.info("MQTT disconnected!")
