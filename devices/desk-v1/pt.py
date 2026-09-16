import asyncio, time
from machine import Pin
from pushbutton import Pushbutton


async def btn_click(something: str):
    print(f"[{time.ticks_ms()}] BTN Click: {something}")

async def nothing():
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    pin = Pin(4, Pin.IN)
    pb = Pushbutton(pin, suppress=True)

    pb.press_func(btn_click, ('press',))
    pb.release_func(btn_click, ("release",))
    pb.double_func(btn_click, ("double",))
    pb.long_func(btn_click, ("long",))

    try:
        print("START")
        asyncio.run(nothing())
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        asyncio.new_event_loop()
