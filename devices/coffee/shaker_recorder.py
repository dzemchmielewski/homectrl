import asyncio
import time
from machine import Pin


SHAKER_PIN = 32
POLL_INTERVAL_MS = 5
SAVE_INTERVAL_MS = 2_000
OUTPUT_FILE = 'shaker.csv'


class ShakerRecorder:
    def __init__(self, pin_num: int = SHAKER_PIN, output_file: str = OUTPUT_FILE,
                 interval_ms: int = SAVE_INTERVAL_MS, poll_ms: int = POLL_INTERVAL_MS):
        self._pin = Pin(pin_num, Pin.IN)
        self._output_file = output_file
        self._interval_ms = interval_ms
        self._poll_ms = poll_ms
        self._changes = []
        self.led = Pin(33, Pin.OUT)
        self.led.off()

    async def run(self):
        print(f'[shaker] polling pin every {self._poll_ms} ms, saving to {self._output_file} every {self._interval_ms} ms')
        with open(self._output_file, 'w') as f:
            f.write('ticks_ms,value\n')

        last_value = self._pin.value()
        last_save = time.ticks_ms()

        while True:
            await asyncio.sleep_ms(self._poll_ms)

            current = self._pin.value()
            if current != last_value:
                last_value = current
                self._changes.append((time.ticks_ms(), current))

            if time.ticks_diff(time.ticks_ms(), last_save) >= self._interval_ms:
                self.led.toggle()
                last_save = time.ticks_ms()
                if not self._changes:
                    print('[shaker] no changes')
                    continue
                batch, self._changes = self._changes, []
                with open(self._output_file, 'a') as f:
                    for ticks, val in batch:
                        f.write(f'{ticks},{val}\n')
                print(f'[shaker] saved {len(batch)} changes')


if __name__ == '__main__':
    asyncio.run(ShakerRecorder().run())