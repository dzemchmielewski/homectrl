import time
import logging
from machine import Pin, PWM
from bit_matrix import BitMatrix


class TxCarrier:
    def pulse(self, duration_us: int):
        logging.error(f"Burst pulse not implemented! Duration: {duration_us}us")
    def deinit(self):
        pass


class PWMCarrier(TxCarrier):
    def __init__(self, pin: Pin, freq: int = 38000, duty: int = 512):
        self.duty = duty
        self.pwm = PWM(pin, freq=freq, duty=0)

    def pulse(self, duration_us: int):
        self.pwm.duty(self.duty)
        time.sleep_us(duration_us)
        self.pwm.duty(0)

    def deinit(self):
        self.pwm.deinit()

class PinCarrier(TxCarrier):
    def __init__(self, pin: Pin):
        self.pin = pin

    def pulse(self, duration_us: int):
        self.pin.on()
        time.sleep_us(duration_us)
        self.pin.off()

class IrNecTx:

    BURST = 562
    ONE = 1687
    ZERO = 562
    SIZE = 67

    def __init__(self, carrier: TxCarrier):
        self.carrier = carrier
        self.times = [0 for _ in range(IrNecTx.SIZE)]
        self.matrix = BitMatrix(4, 8)

    def deinit(self):
        self.carrier.deinit()

    def send(self, addr: int, cmd: int, repeat: int = 0):
        for row, num in enumerate((addr, ~addr, cmd, ~cmd)):
            for col in range(8):
                self.matrix.set(row, col, (num >> col) & 1)

        value = self.matrix.to_int()
        logging.debug('')
        logging.debug(self.matrix)
        print(self.matrix.to_bits())

        self.times[0] = 9_000
        self.times[1] = 4_500
        for i in range(32):
            self.times[2 + (2 * i)] = IrNecTx.BURST
            self.times[2 + (2 * i) + 1] = IrNecTx.ONE if (value >> i) & 1 == 1 else IrNecTx.ZERO
        self.times[IrNecTx.SIZE - 1] = IrNecTx.BURST

        start_time = time.ticks_us()
        for i in range(0,  IrNecTx.SIZE - 1, 2):
            self.carrier.pulse(self.times[i])
            time.sleep_us(self.times[i + 1])
        self.carrier.pulse(self.times[IrNecTx.SIZE - 1])
        end_time = time.ticks_us()
        logging.debug("Sending time: {}us".format(end_time - start_time))

        # Repeat
        if repeat > 0:
            time.sleep_us(40_000)
            for i in range(repeat):
                self.carrier.pulse(9_000)
                time.sleep_us(2_250)
                self.carrier.pulse(IrNecTx.BURST)
                if i + 1 < repeat:
                    time.sleep_us(98_188) # Fill to 110ms


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("%(message)s"))

    pin = Pin(3, Pin.OUT, value = 0)
    tx = IrNecTx(PinCarrier(pin))
    try:
        tx.send(0x0080, 0x01)
    finally:
        tx.deinit()
