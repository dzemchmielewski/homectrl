import asyncio
import time

from buzz_player import BuzzPlayer


async def my_cool_main_loop(buz: BuzzPlayer):
    for i in range(8):
        print(f"{time.ticks_ms()/1_000} Doing something...")
        await asyncio.sleep(1)
    buz.stop()

async def main_async():
    p = BuzzPlayer(3)
    tasks = [
        asyncio.create_task(p.play_song_async('StarWars')),
        asyncio.create_task(my_cool_main_loop(p))]
    for t in tasks:
        await t

if __name__ == "__main__":
    # synch:
    # BuzzPlayer(3).play_song('StarWars')

    # async:
    asyncio.run(main_async())

