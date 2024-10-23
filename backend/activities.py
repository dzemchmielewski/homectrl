import datetime
import time
from collections import deque
import human_readable as hr

from backend.sms import SMS
from backend.storage import Laundry, model_to_dict, Electricity
from backend.tools import json_deserial, json_serial, MQTTClient
from common.common import Common
from configuration import Topic


class LaundryActivity(Common):
    INPUT_TOPIC = Topic.OnAir.format("electricity", "bathroom")
    OUTPUT_TOPIC = Topic.OnAir.format(Topic.OnAir.Facet.activity, "laundry")

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
        self.floating_start_time = None
        self.start_parameters = None

    def threshold_crossed(self):
        l = list(self.active_power_queue)
        return (sum(l)/len(l)) >= 3

    def on_message(self, topic, data):
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

