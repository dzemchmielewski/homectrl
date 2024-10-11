import datetime
import time
from collections import deque
import human_readable as hr

from backend.sms import SMS
from backend.storage import Laundry, model_to_dict, Electricity
from backend.tools import json_deserial, json_serial, MQTTClient
from common.common import Common
from configuration import Configuration


class LaundryActivity(Common):
    INPUT_TOPIC = Configuration.TOPIC_ONAIR + "/electricity/bathroom"
    OUTPUT_TOPIC = Configuration.TOPIC_ACTIVITY + "/laundry"

    def __init__(self, mqtt: MQTTClient):
        super().__init__("Laundry", debug=False)
        self.sms = SMS()
        self.mqtt = mqtt
        self.active_laundry = None
        self.laundry = Laundry.get_last()
        if self.laundry is None:
            self.laundry = Laundry()
        self.publish()
        self.active_power_queue = deque((), 2)

    @staticmethod
    def is_on(active_power_list: list):
        return (sum(active_power_list)/len(active_power_list)) >= 3

    def on_message(self, topic, data):
        self.active_power_queue.append(data["active_power"])
        is_on = self.is_on(list(self.active_power_queue))
        if not self.laundry.is_active() and is_on:
            # Laundry has started!
            self.laundry = Laundry(start_at=data["create_at"], start_energy=data["active_energy"])
            self.laundry.save(force_insert=True)
            self.publish()
        elif self.laundry.is_active() and not is_on:
            # Laundry has finished!
            self.laundry.end_at = data["create_at"]
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
        self.debug("PUBLISH {} -> {}".format(self.OUTPUT_TOPIC, message))
        self.mqtt.publish(self.OUTPUT_TOPIC, message, retain=True)


class Activities(Common):

    def __init__(self):
        super().__init__("Activities")
        self.start_at = datetime.datetime.now()
        self.status = None
        self.exit = False
        self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
        self.activities = [LaundryActivity(self.mqtt)]

    def on_message(self, client, userdata, msg):
        self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
        data = json_deserial(msg.payload.decode())
        for activity in self.activities:
            if activity.INPUT_TOPIC == msg.topic:
                activity.on_message(msg.topic, data)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
        for activity in self.activities:
            client.subscribe(activity.INPUT_TOPIC)

    def on_disconnect(self, *args, **kwargs):
        self.log("MQTT disconnected!")

    def stop(self):
        self.exit = True

    def start(self):
        self.mqtt.loop_start()
        while not self.exit:
            time.sleep(0.5)
        self.mqtt.disconnect()
        self.mqtt.loop_stop()


# class Database2MQTT(Common):
#
#     def __init__(self):
#         super().__init__("Database2MQTT", debug=True)
#         self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
#
#     def run(self):
#         for entry in Electricity.select().order_by(Electricity.create_at.asc()):
#             self.mqtt.publish(
#                 "homectrl/temp/electricity/bathroom",
#                 json_serial(model_to_dict(entry)),
#                 retain=False)
#             print("ID: {}".format(entry.id))
#
#     def on_message(self, client, userdata, msg):
#         self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
#
#     def on_connect(self, client, userdata, flags, reason_code, properties):
#         self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
#
#     def on_disconnect(self, *args, **kwargs):
#         self.log("MQTT disconnected!")

# class ReprocessMQTTMessage(Common):
#
#     def __init__(self):
#         super().__init__("ReprocessMQTTMessage", debug=True)
#         self.mqtt = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
#
#     def run(self):
#         exit = False
#         self.mqtt.loop_start()
#         while not exit:
#             try:
#                 time.sleep(0.5)
#             except KeyboardInterrupt:
#                 exit = True
#         self.mqtt.disconnect()
#         self.mqtt.loop_stop()
#
#     def on_message(self, client, userdata, msg):
#         self.debug("[{}]{}".format(msg.topic, msg.payload.decode()))
#         data = json_deserial(msg.payload.decode())
#         data["start_at"] = datetime.datetime.fromisoformat(data["start_at"])
#         data["end_at"] = datetime.datetime.fromisoformat(data["end_at"])
#
#         data["duration"] = hr.precise_delta(data["end_at"] - data["start_at"], formatting=".0f")
#         data["energy"] = (data["end_energy"] - data["start_energy"]) / 1000
#         message = json_serial(data)
#         self.log("PUBLISH {} -> {}".format("todo", message))
#         self.mqtt.publish("homectrl/onair/activity/laundry", message, retain=True)
#
#     def on_connect(self, client, userdata, flags, reason_code, properties):
#         self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}")
#         self.mqtt.subscribe("homectrl/onair/activity/temp")
#
#     def on_disconnect(self, *args, **kwargs):
#         self.log("MQTT disconnected!")
#
# from backend.activities import ReprocessMQTTMessage
# ReprocessMQTTMessage().run()

