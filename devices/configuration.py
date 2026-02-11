import json


class Configuration:

    MQTT_USERNAME = None
    MQTT_PASSWORD = None

    MQTT_SERVER = "192.168.0.24"
    TOPIC_HOMECTRL = "homectrl"
    TOPIC_HOMECTRL_ONAIR = TOPIC_HOMECTRL + "/onair"
    TOPIC_HOMECTRL_ONAIR_ACTIVITY = TOPIC_HOMECTRL_ONAIR + "/activity"
    TOPIC_ROOT = TOPIC_HOMECTRL + "/device/{}"

    NTP_SERVER = "status.home"
    # NTP_SERVER = "pool.ntp.org"

    WEBREPL_PASSWORD = None

    WIFI_SSID = None
    WIFI_PASSWORD = None

    AP_SSID = None
    AP_PASSWORD = None

    secrets = None

    try:
        with open('secrets.json') as file:
            secrets = json.loads(file.read())
            MQTT_USERNAME = secrets.get('mqtt_username')
            MQTT_PASSWORD = secrets.get('mqtt_password')
            WEBREPL_PASSWORD = secrets.get('webrepl_password')
            WIFI_SSID = secrets.get('wifi_ssid')
            WIFI_PASSWORD = secrets.get('wifi_password')
            AP_SSID = secrets.get('ap_ssid')
            AP_PASSWORD = secrets.get('ap_password')

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

