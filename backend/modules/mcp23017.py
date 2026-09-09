from modules.bit_matrix import *
from gpiozero import DigitalOutputDevice, DigitalInputDevice


class Config:
    # IODIRA/B (0x00/0x01) — pin direction. Bit=1 → input, bit=0 → output.
    # Default: all pins input (safe power-on state)
    direction ="direction"

    # IPOLA/B (0x02/0x03) — input polarity. Bit=1 → GPIO read is inverted
    # relative to actual pin state. Only affects pins set as input. Default: no inversion
    polarity = "polarity"

    # GPINTENA/B (0x04/0x05) — interrupt-on-change enable. Bit=1 → arm interrupt on that pin.
    # Default: all interrupts disabled
    int_enable = "int_enable"

    # DEFVALA/B (0x06/0x07) — reference value for comparison-mode interrupts.
    # Only used when the matching INTCON bit = 1. Default: 0x00
    int_defval = "int_defval"

    # INTCONA/B (0x08/0x09) — interrupt trigger mode per pin.
    # Bit=0 → compare against previous value (fires on any change)
    # Bit=1 → compare against DEFVAL (fires only on mismatch with reference)
    int_control = "int_control"

    # IOCON (0x0A, mirrored at 0x0B in BANK=0 mode) — global chip configuration,
    # not per-bank. Default: 0x00
    #   bit7 BANK   — register addressing mode. 0 = interleaved A/B (this map's layout),
    #                 1 = separate A/B blocks at different addresses. Changing this
    #                 shifts every other register's address — handle with care.
    #   bit6 MIRROR — 1 = INTA and INTB are OR'd together internally, so either bank's
    #                 interrupt appears on both physical INT pins (useful with a single
    #                 INT line wired back to the MCU).
    #   bit5 SEQOP  — 0 = address pointer auto-increments on multi-byte read/write
    #                 (required for the block reads/writes used here). 1 = disables
    #                 auto-increment, pointer stays fixed.
    #   bit4 DISSLW — 1 = disables SDA slew-rate control on the I2C bus. Leave at
    #                 default (0) unless you have a specific signal-integrity reason.
    #   bit3 HAEN   — hardware address enable. Only relevant on the SPI variant
    #                 (MCP23S17); no effect on the I2C part.
    #   bit2 ODR    — 1 = INT pin(s) configured as open-drain output (allows
    #                 wired-OR with other INT lines via an external pull-up).
    #                 Overrides INTPOL when set.
    #   bit1 INTPOL — INT pin active polarity when ODR=0: 1 = active-high,
    #                 0 = active-low. No effect when ODR=1 (open-drain).
    #   bit0 —        unimplemented, reads as 0.
    config = "config"

    # GPPUA/B (0x0C/0x0D) — internal 100kΩ pull-up enable.
    # Only effective on pins configured as input. Default: disabled
    pullup = "pullup"


class OutputRegister:

    # INTFA/B — read-only. Bit=1 marks the pin that caused
    # the pending interrupt. Tells you *which* pin, not its value.
    # 0x0E, 0x0F
    INTF = 0x0E

    # INTCAPA/B — read-only snapshot of GPIO state at the moment
    # the interrupt fired. Reading this clears the interrupt condition,
    # so read it first in the ISR handler before the value can change.
    # 0x10, 0x11
    INTCAP = 0x10

    # GPIOA/B — live pin state (input pins reflect the physical pin,
    # output pins reflect OLAT). Reading this also clears a pending
    # interrupt if the pin has already returned to its non-trigger state.
    # 0x12, 0x13
    GPIO = 0x12

    # OLATA/B — output latch. Holds the driven value for pins configured
    # as outputs (IODIR=0); writing here sets output pin state directly.
    # 0x14, 0x15
    OLAT = 0x14


class Values(BitMatrix):
    def __init__(self, bank_a: int = 0, bank_b: int = 0, reverse = True):
        if reverse:
            super().__init__(2, 8, (self.reverse_bits(bank_a) << 8) | self.reverse_bits(bank_b))
        else:
            super().__init__(2, 8, (bank_a << 8) | bank_b)

    def __repr__(self):
        return f"{'{0:08b}'.format(self.get(0))} {'{0:08b}'.format(self.get(1))}"

    def set(self, value: int, bank: int):
        BitMatrix.set(self, value, x=None, y=bank)

    @staticmethod
    def reverse_bits(x: int, width: int = 8) -> int:
        result = 0
        for _ in range(width):
            result = (result << 1) | (x & 1)
            x >>= 1
        return result


class MCP23017:

    def __init__(self, address, i2c, enable_pin: int | None = None, alert_a: int | None = None, alert_b: int | None = None):
        self.i2c = i2c
        self.address = address
        self._config = None
        self.enable = DigitalOutputDevice(enable_pin, active_high=True, initial_value=True) if enable_pin is not None else None
        self.alert_a = DigitalInputDevice(alert_a) if alert_a is not None else None
        self.alert_b = DigitalInputDevice(alert_b) if alert_b is not None else None

    def _pull_config(self) -> None:
        data = self.i2c.read_block_data(self.address, 0x00, 14)
        if len(data) != 14:
          raise ValueError(f"Expected 14 bytes, got {len(data)}")

        self._config = {
            Config.direction: Values(data[0], data[1]),
            Config.polarity: Values(data[2], data[3]),
            Config.int_enable: Values(data[4], data[5]),
            Config.int_defval: Values(data[6], data[7]),
            Config.int_control: Values(data[8], data[9]),
            Config.config: Values(data[10]),
            Config.pullup: Values(data[12], data[13]),
        }

    @property
    def config(self):
        if self._config is None:
            self._pull_config()
        return self._config

    def push_config(self):
        data = [
            self._config[Config.direction].get(0), self._config[Config.direction].get(1),
            self._config[Config.polarity].get(0), self._config[Config.polarity].get(1),
            self._config[Config.int_enable].get(0), self._config[Config.int_enable].get(1),
            self._config[Config.int_defval].get(0), self._config[Config.int_defval].get(1),
            self._config[Config.int_control].get(0), self._config[Config.int_control].get(1),
            self._config[Config.config].get(0), self._config[Config.config].get(0),
            self._config[Config.pullup].get(0), self._config[Config.pullup].get(1)
        ]
        self.i2c.write_block_data(self.address, 0x00, [Values.reverse_bits(x) for x in data])
        self._pull_config()

    def read(self, register: int):
        data = self.i2c.read_block_data(self.address, register, 2)
        return Values(data[0], data[1])

    def read_output(self):
        data = self.i2c.read_block_data(self.address, OutputRegister.GPIO, 2)
        return Values(data[0], data[1])

    def read_capture(self):
        data = self.i2c.read_block_data(self.address, OutputRegister.INTCAP, 2)
        return Values(data[0], data[1])

    def deinit(self):
        for pin in [self.enable, self.alert_a, self.alert_b]:
            if pin is not None:
                pin.close()


if __name__ == '__main__':
    import time
    import smbus2 as smbus
    from i2c import I2C

    i2c = I2C(smbus.SMBus(1))
    mcp = MCP23017(0x27, i2c, 22)

    time.sleep(1)

    try:
        print(mcp.config)
        mcp.config[Config.polarity].set(0b00000000, 0)
        mcp.config[Config.polarity].set(0b00000000, 1)
        mcp.config[Config.pullup].set(0b11111111, 0)
        mcp.config[Config.pullup].set(0b11110000, 1)
        #
        mcp.push_config()
        print(mcp.config)

        while True:
            gpio = mcp.read(OutputRegister.GPIO)
            print(gpio.__repr__())
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        mcp.deinit()

