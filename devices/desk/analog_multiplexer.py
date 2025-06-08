from toolbox.pinio import PinIO


class AnalogMultiplexer:

    def __init__(self, setup_pins: [int], enable_pin: int = None, signal_pin: int = None, channels_range: int = None):
        self.pins = setup_pins
        self.pinsIO = [PinIO(p, False) for p in self.pins]
        self.enable_pin = PinIO(enable_pin) if enable_pin else None
        self.signal_pin = PinIO(signal_pin) if signal_pin else None

        self.channels_range = min(channels_range, pow(2, len(self.pins))) if channels_range else pow(2, len(self.pins))
        self.bin_format = f"{{:0{len(self.pins)}b}}"
        self.log("AnalogMultiplexer {}-channel initialization  ({}) <-> GPIO BCM({})".format(
            self.channels_range,
            " ".join(["s{}".format(i) for i in reversed(range(0, len(self.pins)))]),
            " ".join(["{}".format(x) for x in self.pins])
        ))

    def log(self, message):
        # print(message)
        pass

    def set_channel(self, channel: int):
        if channel < 0 or channel > self.channels_range - 1:
            raise ValueError("Channel number must be an integer between 0 and {}. Provided: {}".format(self.channels_range - 1, channel))

        bin_channel = self.bin_format.format(channel)
        self.log("CHANNEL: {}, PIN inputs ({}): {}".format(channel, " ".join(["s{}".format(i) for i in reversed(range(0, len(self.pins)))]), bin_channel))

        for i in range(0, len(bin_channel)):
            signal = 1 if bin_channel[i:i + 1] == "1" else 0
            self.pinsIO[i].set(signal)
            self.log("s{} GPIO{} -> {}".format(3-i, self.pins[i], signal))

    def turn_on(self):
        if self.enable_pin:
            self.enable_pin.off()

    def turn_off(self):
        if self.enable_pin:
            self.enable_pin.on()

    def read_on(self) -> [int]:
        result = []
        for i in range(self.channels_range):
            self.turn_off()
            self.set_channel(i)
            self.turn_on()
            if self.signal_pin.get():
                result.append(i)
        return result

    def set_on(self, channel):
        self.set_channel(channel)
        if self.signal_pin:
            self.signal_pin.on()

