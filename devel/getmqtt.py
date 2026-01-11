import asyncio
import json
import logging
import os

from backend.tools import MQTTClient
from configuration import Topic

logger = logging.getLogger("devel.getmqtt")

class GetMQTT:

    def __init__(self):
        self.path = os.path.realpath(os.path.dirname(__file__) + '/../devices/meteo/') + '/'
        self.grab = {
            'astro': {
                'topic': Topic.OnAir.format(Topic.OnAir.Facet.activity, "astro"),
                'data': None,
                'filename': 'astro.json'
            },
            'meteo': {
                'topic': Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo"),
                'data': None,
                'filename': 'meteo.json'
            },
            'precipitation': {
                'topic': Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo/precipitation"),
                'data': None,
                'filename': 'precipitation.json'
            },
            'temperature': {
                'topic': Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo/temperature"),
                'data': None,
                'filename': 'temperature.json'
            },
            'pressure': {
                'topic': Topic.OnAir.format(Topic.OnAir.Facet.activity, "meteo/pressure"),
                'data': None,
                'filename': 'pressure.json'
            },
        }

    def on_connect(self, client, userdata, flags, reason_code, properties):
        logger.info("Connected with result code " + str(reason_code))
        for key in self.grab:
            topic = self.grab[key]['topic']
            logger.info(f"Subscribing to topic {topic}")
            client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        logger.info(f"Message received on topic {msg.topic}")
        for key in self.grab:
            topic = self.grab[key]['topic']
            if msg.topic == topic:
                self.grab[key]['data'] = msg.payload.decode()
                logger.info(f"Grabbed data for {key}: {self.grab[key]['data']}")

    def on_disconnect(self, *args, **kwargs):
        logger.info("Disconnected from MQTT broker")

    def is_grabbed(self):
        return all(self.grab[key]['data'] is not None for key in self.grab)

    def save_grabbed_data(self):
        for key in self.grab:
            filename = self.path + self.grab[key]['filename']
            data = json.loads(self.grab[key]['data'])
            with open(filename, 'w') as f:
                f.write(json.dumps(data, indent=2))
            logger.info(f"Saved data for {key} to {filename}")

    async def main(self):
        client = MQTTClient(on_connect=self.on_connect, on_message=self.on_message, on_disconnect=self.on_disconnect)
        client.loop_start()
        try:
            # client.loop_forever()
            while not self.is_grabbed():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
        if self.is_grabbed():
            self.save_grabbed_data()
