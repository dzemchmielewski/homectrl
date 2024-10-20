import traceback
import sys
import time
from backend.storage import *
from common.common import Common
from configuration import Configuration
from backend.tools import json_serial, json_deserial, singleton, MQTTClient


@singleton
class OnAir(Common):

    def __init__(self):
        super().__init__("OnAir", debug=False)
        self.start_at = datetime.datetime.now()
        self.status = {}
        self.exit = False
        self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)

    def on_message(self, client, userdata, msg):
        try:
            self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))

            data = json_deserial(msg.payload.decode())

            if data.get("name") is None:
                data["name"] = msg.topic.split("/")[2]

            data["timestamp"] = datetime.datetime.now()

            for entry in self.data2entries(data):
                current = self.status[type(entry)].get(entry.name.value)
                if not entry.equals(current):
                    self.debug("SWITCH {} for {}".format(type(entry), entry.name.value))
                    self.process_entry(entry)

        except BaseException as e:
            self.log("Exception caught! {}".format(e))
            self.log("On message: [{}]{}".format(msg.topic, msg.payload.decode()))
            traceback.print_exc()
            # for line in traceback.format_stack():
            #     print(line.strip())

    @staticmethod
    def data2entries(data: dict) -> [HomeCtrlValueBaseModel]:
        result = [Live(name=data["name"], create_at=data["timestamp"], value=data.get("live") is None or data.get("live"))]
        for key, value in data.items():
            if key in ["temperature", "humidity", "darkness", "light", "presence", "pressure", "voltage", "error"]:
                clazz = getattr(sys.modules[__name__], key.capitalize())
                result.append(clazz(name=data["name"], create_at=data["timestamp"], value=value))
            elif key == "radar":
                result.append(Radar(name=data["name"], create_at=data["timestamp"],
                                    presence=value["presence"], target_state=value["target_state"],
                                    # move_distance=value["move"]["distance"], move_energy=value["move"]["energy"],
                                    # static_distance=value["static"]["distance"], static_energy=value["static"]["energy"],
                                    distance=value["distance"]))
            elif key == "radio":
                result.append(Radio(name=data["name"], create_at=data["timestamp"],
                                    station_name=value["station"]["name"], station_code=value["station"]["code"],
                                    volume=value["volume"]["volume"], muted=value["volume"]["is_muted"], playinfo=value["playinfo"]))
            elif key == "electricity":
                result.append(Electricity(name=data["name"], create_at=data["timestamp"],
                                          voltage=value["voltage"], current=value["current"], active_power=value["active_power"],
                                          active_energy=value["active_energy"], power_factor=value["power_factor"]))
        return result

    def process_entry(self, entry: HomeCtrlBaseModel, db_save=True):
        self.status[type(entry)][entry.name.value] = entry
        subject = Configuration.TOPIC_ONAIR + "/" + type(entry).__name__.lower() + "/" + entry.name.value
        self.debug("PUBLISH {} -> {}".format(subject, model_to_dict(entry)))
        if db_save:
            entry.save_new_value()
        self.mqtt.publish(
            subject,
            json_serial(model_to_dict(entry)),
            retain=True)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
        for topic in Configuration.ONAIR_TOPIC_SUBSCRIPTIONS:
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
