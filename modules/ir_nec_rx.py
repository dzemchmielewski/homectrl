import asyncio
import logging
import time
from machine import Pin, Timer

from bit_matrix import BitMatrix


class IrNecRx:

    EDGES_NUM = 68

    def __init__(self, pin: Pin, callback):
        self.pin = pin
        self.pin.irq(handler=self._read, trigger=(Pin.IRQ_FALLING | Pin.IRQ_RISING))
        self.timer = Timer(0)
        self.index = 0
        self.reading = [0 for _ in range(IrNecRx.EDGES_NUM - 2)]
        self.last_tick = 0
        self.callback = callback
        self.last_value = (None, None)
        logging.info("Listening for IR signals...")

    def _read(self, _):
        t = time.ticks_us()
        if self.index == 0:
            self.timer.init(period=75, mode=Timer.ONE_SHOT, callback=self._read_end)
            self.last_tick = t
        elif self.index < IrNecRx.EDGES_NUM - 1:
            self.reading[self.index - 1] = time.ticks_diff(t, self.last_tick)
            self.last_tick = t
        self.index += 1

    def _read_end(self, _):
        result = self.decode()
        self.index = 0
        if result:
            addr, cmd, repeat = result
            if not repeat:
                self.last_value = (addr, cmd)
            self.callback(*self.last_value, repeat)
        else:
            self.last_value = (None, None)

    def deinit(self):
        self.pin.irq(handler=None)

    def decode(self) -> (int, int, bool):
        # logging.debug(f"IR signal detected, edges: {self.index}")
        # logging.debug(f"Reading: {self.reading[0:self.index]}")
        matrix = BitMatrix(4, 8)
        matrix.number = 0
        if self.index == IrNecRx.EDGES_NUM:
            if self.reading[0] < 8000:
                logging.error(f"Protocol error - the header burst ({self.reading[0]}) is too short (<8000)")
                return None
            if self.reading[1] < 3000:
                logging.error(f"Protocol error - the header space ({self.reading[1]}) is too short (<3000)")
                return None

            for i in range(2, 68 - 2, 2):
                matrix.number >>= 1
                if self.reading[i+1] > 1200:
                    matrix.number |= 0x80000000
            # logging.debug(matrix)
            # logging.debug(matrix.number)
            (addr, addr_neg, cmd, cmd_neg) =  (
                                                      (matrix.number >> 0) & 0xff,
                                                      (matrix.number >> 8) & 0xff,
                                                      (matrix.number >> 16) & 0xff,
                                                      (matrix.number >> 24) & 0xff)
            if addr & addr_neg != 0:
                logging.error(f"Communication error - the address check failed. addr: {bin(addr)}, ~addr: {bin(addr_neg)}")
                return None
            if cmd & cmd_neg != 0:
                logging.error(f"Communication error - the command check failed. cmd: {bin(cmd)}, ~cmd: {bin(cmd_neg)}")
                return None
            return addr, cmd, False

        elif self.index == 4:
            return None, None, True

        else:
            logging.error(f"Unexpected block size: {self.index}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(logging.Formatter("%(message)s"))

    def ir_input(addr, cmd, repeat):
        logging.info(f"ADDRESS: {hex(addr) if addr is not None else "----"}, COMMAND: {hex(cmd) if cmd is not None else "----"}, REPEAT: {repeat}")

    ir = IrNecRx(Pin(2, Pin.IN), ir_input)

    exit = False
    async def nothing():
        while not exit:
            await asyncio.sleep(1)

    try:
        asyncio.run(nothing())
    except KeyboardInterrupt:
        logging.info("SIGINT")
    finally:
        exit = True
        ir.deinit()
        asyncio.get_event_loop().run_until_complete(nothing())
        logging.info("END")

