import json


class Configuration:

    MQTT_USERNAME = None
    MQTT_PASSWORD = None

    MQTT_SERVER = "192.168.0.24"
    TOPIC_ROOT = "homectrl/device/{}"

    NTP_SERVER = "status.home"

    WEBREPL_PASSWORD = None

    WIFI_SSID = None
    WIFI_PASSWORD = None

    secrets = None

    try:
        with open('secrets.json') as file:
            secrets = json.loads(file.read())
            MQTT_USERNAME = secrets['mqtt_username']
            MQTT_PASSWORD = secrets['mqtt_password']
            WEBREPL_PASSWORD = secrets['webrepl_password']
            WIFI_SSID = secrets['wifi_ssid']
            WIFI_PASSWORD = secrets['wifi_password']

    except Exception as e:
        print("FATAL ERROR when loading secrets.json: {}".format(e))

    @staticmethod
    def topics(name: str) -> tuple:
        topic = Configuration.TOPIC_ROOT.format(name)
        return (
            topic + "/live",
            topic + "/data",
            topic + "/state",
            topic + "/capabilities",
            topic + "/control")

