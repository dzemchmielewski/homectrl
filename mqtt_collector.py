from threading import Thread
from time import sleep
import datetime
from paho.mqtt import client as mqtt_client
from common.common import Common
from common.communication import SocketCommunication
from common.server import CommonServer
from homectrl import Configuration, json_serial, json_deserial
import storage


class MQTTSubscriber(Common):

    def __init__(self, debug=False):
        super().__init__("MQTT subscriber", debug)
        self.exit = False
        self.last_value = None

    def on_message(self, client, userdata, msg):
        self.debug("[{}][{}]".format(msg.topic, msg.payload.decode()))

        data = json_deserial(msg.payload.decode())
        if data.get("name") is None:
            data["name"] = msg.topic.split('/')[1]

        if (error := data.get("error")) is not None:
            self.log("[{}] {}".format(data["name"], error))
        else:
            data["timestamp"] = datetime.datetime.now()

        self.last_value = data
        storage.save(data)

    def run(self):
        conf = Configuration.MAP["mqtt"]
        client = mqtt_client.Client("collector")
        client.username_pw_set(conf["username"], conf["password"])
        client.connect(conf["host"], conf["port"])
        client.on_message = self.on_message
        client.subscribe("homectrl/#")
        client.loop_start()
        while not self.exit:
            sleep(2)
        client.loop_stop(force=True)
        client.disconnect()


class MQTTCollectorServer(CommonServer):

    def __init__(self):
        conf = Configuration.MAP["collector"]
        super().__init__("MQTT_COLLECTOR",
                         SocketCommunication("conn", conf["host"], conf["port"], is_server=True, debug=conf["debug"]))
        self.subscriber = MQTTSubscriber(conf["debug"])
        self.subscriber_thread = Thread(target=self.subscriber.run)
        self.subscriber_thread.start()

    def on_exit(self):
        self.subscriber.exit = True
        self.subscriber_thread.join()

    def handle_help(self):
        return "COLLECTOR COMMANDS: info, go, nogo"

    def handle_message(self, msg):
        cmd = msg.strip().upper()

        if cmd == "INFO":
            answer = {
                "is_alive": self.subscriber_thread.is_alive(),
                "last_value": self.subscriber.last_value
            }

        elif cmd.startswith("GO"):
            if not self.subscriber_thread.is_alive():
                self.subscriber_thread = Thread(target=self.subscriber.run)
                self.subscriber_thread.start()
                answer = {"status": "ok"}
            else:
                answer = {"status": "error", "message": "Collector thread is already working"}

        elif cmd.startswith("NOGO"):
            if self.subscriber_thread.is_alive():
                self.subscriber.exit = True
                self.subscriber_thread.join()
                answer = {"status": "ok"}
            else:
                answer = {"status": "error", "message": "Collector thread is not alive"}

        else:
            answer = {"status": "error", "message": "Unknown command: {}".format(msg)}

        return json_serial(answer)


if __name__ == "__main__":
    collector = MQTTCollectorServer()
    try:
        collector.start()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        collector.on_exit()
