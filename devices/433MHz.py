import asyncio
import random

from machine import Pin, UART

EXIT = False

class TX:
    def __init__(self, uart: UART):
        self._tx  = uart
        self.swriter = asyncio.StreamWriter(uart)


    async def write(self, text: str):
        while not EXIT:
            # msg = (text.format(random.randint(20,25), random.randint(0, 100)) + '\n').encode()
            msg = text.format(random.randint(20,25), random.randint(0, 100)) + '\n'
            print(f"WRITE: {msg}", end='')
            # self._tx.write(msg)
            self.swriter.write(msg)
            await self.swriter.drain()
            await asyncio.sleep_ms(5_000)


class RX:
    def __init__(self, uart: UART):
        self._rx  = uart
        self.sreader = asyncio.StreamReader(uart)

    async def read(self):
        while True:
            res = await self.sreader.readline()
            parsed = self._parse(res)
            print(f" READ: {parsed}")

    @staticmethod
    def _parse(bts):
        start, end = -1, -1
        for i, char in enumerate(bts):
            if char == ord('{'):
                start = i
            if char == ord('}'):
                end = i + 1
        if 0 <= start < end and end >= 0:
            try:
                return bts[start:end].decode()
            except UnicodeError:
                pass
        return None


async def nothing():
    try:
        await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

async def main():
    uart  = UART(1, baudrate=512, tx=21, rx=0)
    #uart  = UART(1, baudrate=110, tx=21, rx=0)
    asyncio.create_task(RX(uart).read())
    asyncio.create_task(TX(uart).write("{{temperature: {}.{}}}"))
    while True:
        await asyncio.sleep_ms(100)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("SIGINT")
finally:
    EXIT = True
    asyncio.get_event_loop().run_until_complete(nothing())
    print("END")
