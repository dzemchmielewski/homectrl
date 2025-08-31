import asyncio

from machine import Pin, PWM
import time

from pwm_gamma import PWMGamma

p = PWM(Pin(0), 5000)
p.duty(0)
pwm_gamma = PWMGamma(p)


async def work():
    try:
        print("fade in")
        start = time.ticks_ms()
        task = asyncio.create_task(pwm_gamma.fade(50, 50/2))
        print(f"Fade done in {time.ticks_diff(time.ticks_ms(), start)} ms")

        await asyncio.sleep_ms(1_000)
        print("cancel in")
        task.cancel()
        print("cancel out")

        print("fade out")
        start = time.ticks_ms()
        await pwm_gamma.fade(0, 50/5)
        print(f"Fade done in {time.ticks_diff(time.ticks_ms(), start)} ms")
    finally:
        p.deinit()


async def main_async():
    await asyncio.create_task(work())

if __name__ == "__main__":
    asyncio.run(main_async())


# async def foo(i:int):
#     print(f"foo {i} start")
#     await asyncio.sleep_ms(100)
#     print(f"foo {i} end")
#
# async def bar():
#     print("bar start")
#     await foo(1)
#     print("bar 1-2")
#     await foo(2)
#     print("bar end")
#
#
# asyncio.run(bar())
#


