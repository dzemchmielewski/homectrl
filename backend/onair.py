import traceback
import sys
import time
from backend.storage import *
from common.common import Common
from configuration import Topic
from backend.tools import json_serial, json_deserial, singleton, MQTTClient


@singleton
class OnAir(Common):

    MQTT_SUBSCRIPTIONS = [
        Topic.Device.format("+", Topic.Device.Facility.live),
        Topic.Device.format("+", Topic.Device.Facility.data),
        Topic.Device.format("+", Topic.Device.Facility.capabilities),
        Topic.Device.format("+", Topic.Device.Facility.state)
    ]

    def __init__(self):
        super().__init__("OnAir", debug=False)
        self.start_at = datetime.datetime.now()
        self.status = {}
        # self.capabilities = {}
        # self.state = {}
        self.exit = False
        self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)

    def on_message(self, client, userdata, msg):
        try:
            self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
            data = json_deserial(msg.payload.decode())
            device, facility_str = Topic.Device.parse(msg.topic)
            facility = Topic.Device.Facility(facility_str)

            if facility in [Topic.Device.Facility.live, Topic.Device.Facility.data]:
                if data.get("name") is None:
                    data["name"] = device
                data["timestamp"] = datetime.datetime.now()

                for entry in self.data2entries(data):
                    current = self.status[type(entry)].get(entry.name.value)
                    if not entry.equals(current):
                        self.debug("SWITCH {} for {}".format(type(entry), entry.name.value))
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
                self.log("ERROR! Topic not recognized: {}".format(msg.topic))

        except UnicodeError as e:
            self.log("Unicode error caught! {}".format(e))
            self.log("On message: [{}]{}".format(msg.topic, msg.payload))
            traceback.print_exc()

        except Exception as e:
            self.log("Exception caught! {}".format(e))
            self.log("On message: [{}]{}".format(msg.topic, msg.payload.decode()))
            traceback.print_exc()
            # for line in traceback.format_stack():
            #     print(line.strip())

    @staticmethod
    def data2entries(data: dict) -> [HomeCtrlValueBaseModel]:
        result = [Live(name=data["name"], create_at=data["timestamp"], value=data.get("live") is None or data.get("live"))]
        for key, value in data.items():
            if key in ["temperature", "humidity", "darkness", "light", "presence", "pressure", "voltage", "error", "moisture", "doors", "bell"]:
                if value is not None:
                    clazz = getattr(sys.modules[__name__], key.capitalize())
                    result.append(clazz(name=data["name"], create_at=data["timestamp"], value=value))
            elif key == "radar" and value is not None:
                result.append(Radar(name=data["name"], create_at=data["timestamp"],
                                    presence=value["presence"], target_state=value["target_state"],
                                    # move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
                                    # static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
                                    distance=value["distance"]))
            elif key == "radio" and value is not None:
                result.append(Radio(name=data["name"], create_at=data["timestamp"],
                                    station_name=value["station"]["name"], station_code=value["station"]["code"],
                                    volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]))
            elif key == "electricity" and value is not None:
                result.append(Electricity(name=data["name"], create_at=data["timestamp"],
                                          voltage=value["voltage"], current=value["current"], active_power=value["active_power"],
                                          active_energy=value["active_energy"], power_factor=value["power_factor"]))
        return result

    def process_entry(self, entry: HomeCtrlBaseModel, db_save=True):
        self.status[type(entry)][entry.name.value] = entry
        subject = Topic.OnAir.format(type(entry).__name__.lower(), entry.name.value)
        self.debug("PUBLISH {} -> {}".format(subject, model_to_dict(entry)))
        if db_save:
            entry.save_new_value()
        self.mqtt.publish(
            subject,
            json_serial(model_to_dict(entry)),
            retain=True)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
        for topic in self.MQTT_SUBSCRIPTIONS:
            client.subscribe(topic)

    def on_disconnect(self, *args, **kwargs):
        self.log("MQTT disconnected!")

    def stop(self):
        self.exit = True

    def start(self):
        for entity in device_entities():
            self.status[entity] = {}
            for entry in entity.get_currents():
                self.process_entry(entry, False)

        self.mqtt.loop_start()
        while not self.exit:
            time.sleep(0.5)
        self.mqtt.disconnect()
        self.mqtt.loop_stop()
