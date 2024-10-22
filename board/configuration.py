class Configuration:

    MQTT_SERVER = "192.168.0.21"
    MQTT_USERNAME = "mqtt"
    MQTT_PASSWORD = "emkutete"

    TOPIC_ROOT = "homectrl/device/{}"

    @staticmethod
    def topics(name: str) -> tuple:
        topic = Configuration.TOPIC_ROOT.format(name)
        return (
            topic + "/live",
            topic + "/data",
            topic + "/state",
            topic + "/capabilities",
            topic + "/control")

