import machine
import dht
import utime

from common.common import Common, time_ms


class DHTSensor(Common):

    def __init__(self, name, pin, debug=False):
        super().__init__(name, debug=debug)
        self.sensor = dht.DHT22(machine.Pin(pin))
        self.wait = True

    def get(self):
        if not self.wait:
            utime.sleep(1)
            self.wait = False
        self.sensor.measure()
        temperature = self.sensor.temperature()
        humidity = self.sensor.humidity()
        self.debug("temperature: {}, humidity: {}".format(temperature, humidity))
        return temperature, humidity


if __name__ == '__main__':
    try:
        sensor = DHTSensor("DHT", 7)
        prev = None

        while True:
            value = sensor.get()
            if value != prev:
                print("CHANGE to {}".format(value))
                prev = value
            utime.sleep(10)
    except KeyboardInterrupt:
        pass

# exec(open("modules/dht.py").read())
