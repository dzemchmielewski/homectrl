import asyncio
import logging

import machine
import rtttl

# class Buzzer:
#
#     def __init__(self, pwm_pin: int):
#         self.buzzer = machine.PWM(machine.Pin(pwm_pin), freq=550, duty=0)
#
#     def play_tone(self, freq, msec):
#         print('Freq = {:6.1f} msec = {:6.1f}'.format(freq, msec))
#         if freq > 0:
#             self.buzzer.freq(int(freq))
#             self.buzzer.duty(256)
#         time.sleep_ms(int(msec))
#         self.buzzer.duty(0)
#
#     def play_tune(self, tune: rtttl.RTTTL):
#         try:
#             for freq, msec in tune.notes():
#                 self.play_tone(freq, msec)
#         finally:
#             self.buzzer.duty(0)


class BuzzPlayer:

    def __init__(self, pwm_pin: int = 8, song='MahnaMahna', silent: bool = False):
        self.log = logging.getLogger('BuzzPlay')
        self.log.info(f"BuzzPlay init: pin={pwm_pin}, silent={silent}")
        self.buzzer = machine.PWM(machine.Pin(pwm_pin), freq=550, duty=0)
        self.play = False
        self.tune = rtttl.RTTTL(rtttl.find(song))
        self._is_playing = False
        self._player_task = asyncio.create_task(self._player())
        self.silent = silent

    async def _player(self):
        while True:
            if not self._is_playing and self.play and self.tune is not None:
                await self._play()
            await asyncio.sleep_ms(500)

    async def _play(self):
        self._is_playing = True
        while True:
            self.tune.tune_idx = 0
            for freq, msec in self.tune.notes():
                await self.play_tone(freq, msec)
                if not self.play:
                    self._is_playing = False
                    return
            await asyncio.sleep_ms(1_000)

    def deinit(self):
        self.buzzer.duty(0)
        self._player_task.cancel()

    def set_song(self, song: str):
        self.tune = rtttl.RTTTL(rtttl.find(song))

    async def play_tone(self, freq, msec):
        if freq > 0:
            self.log.debug("Freq = {:6.1f} msec = {:6.1f}".format(freq, msec))
            if not self.silent:
                self.buzzer.freq(int(freq))
                self.buzzer.duty(256)
        await asyncio.sleep_ms(int(msec * 0.9))
        self.buzzer.duty(0)
        await asyncio.sleep_ms(int(msec * 0.1))


    def stop(self):
        self.play = False

    def start(self):
        self.play = True

    def toggle(self):
        self.play = not self.play
