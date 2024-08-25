from time import sleep
from paho.mqtt import client as mqtt_client
from common.common import Common
from configuration import Configuration, json_deserial

class Monitor(Common):

    TARGET_STATE = ["  ", " M", " S", "MS"]

    def __init__(self, topic, debug=False):
        super().__init__("MQTT", debug)
        self.topic = topic

    def target_state(self, ts):
        if ts in range(0, 4):
            return self.TARGET_STATE[ts]
        return " ?"

    def on_message(self, client, userdata, msg):
        message = msg.payload.decode()
        self.log("[{}] {}".format(msg.topic, message))

        try:
            data = json_deserial(message)
            if data.get("radar"):
                self.log("[{}][{}][{}][{}][{}][MOV: {:03}cm, {:03}%][STA: {:03}cm, {:03}%][DST: {:03}cm] [{}]".format(
                    msg.topic,
                    " ON" if data["presence"] else "OFF", self.target_state(data["radar"]["target_state"]),
                    "NIGHT" if data["darkness"] else " DAY ",
                    "light  ON" if data["light"] else "light OFF",
                    data["radar"]["move"]["distance"], data["radar"]["move"]["energy"],
                    data["radar"]["static"]["distance"], data["radar"]["static"]["energy"],
                    data["radar"]["distance"], data["read_light_sensors"]))
        except BaseException as e:
            self.log("ERROR! {}", e)

    def on_connect(self, client, userdata, flags, reason_code):
        self.log(f"Connected with result code: {reason_code}, flags: {flags}, userdata: {userdata}, TOPIC: {self.topic}")
        client.subscribe(self.topic)

    def start(self):
        conf = Configuration.get_mqtt_config()
        client = mqtt_client.Client("monitor")
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.username_pw_set(conf["username"], conf["password"])
        client.connect(conf["host"], conf["port"])

        client.loop_start()
        try:
            while True:
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop(force=True)
            client.disconnect()


if __name__ == "__main__":
    monitor = Monitor("homectrl/#")
    try:
        monitor.start()
    except (KeyboardInterrupt, EOFError):
        pass
