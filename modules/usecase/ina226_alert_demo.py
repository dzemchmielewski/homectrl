import sys
import asyncio
import select
from machine import I2C, Pin
from ina226 import INA226

I2C_ID = 0
I2C_SCL_PIN = 0
I2C_SDA_PIN = 1
INA226_ADDR = 0x44

ALERT_PIN_NUM = 2    # ALR
LOAD_PIN_NUM = 21    # user-controlled output

# default 0.1
R_SHUNT_OHMS = 0.01
MAX_EXPECTED_AMPS = 5
CURRENT_ALERT_MA = 1_200

STATUS_PERIOD_MS = 1000

i2c = I2C(I2C_ID, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400_000)
ina = INA226(i2c, addr=INA226_ADDR)
ina.calibrate(r_shunt_ohms=R_SHUNT_OHMS, max_expected_amps=MAX_EXPECTED_AMPS)

# Faster averaging than the driver default (AVG_512) so the demo reacts
# quickly when you flip the load on/off - purely a demo-responsiveness choice.
ina.configure(avg=ina.AVG_16, vbusct=ina.VBUSCT_588US, vshct=ina.VSHCT_588US,
              mode=ina.MODE_SHUNT_BUS_CONTINUOUS)

_alert_threshold_v = (CURRENT_ALERT_MA / 1000.0) * R_SHUNT_OHMS
ina.set_alert(ina.ALERT_SHUNT_OVER, limit_volts=_alert_threshold_v, latch=True)
print("Alert armed: current > {} mA ({:.6f} mV shunt threshold)".format(
    CURRENT_ALERT_MA, _alert_threshold_v * 1000))


load_pin = Pin(LOAD_PIN_NUM, Pin.OUT, value=0)
print("GPIO{} initialised as output, value=0".format(LOAD_PIN_NUM))

alert_pin = Pin(ALERT_PIN_NUM, Pin.IN, Pin.PULL_UP)
alert_flag = asyncio.ThreadSafeFlag()

if alert_pin.value() == 0:
    # A stale latch from a previous run/power-up condition - clear it so we
    # start from a known state instead of waiting for a fresh falling edge.
    ina.read_alert_flags()
    print("Cleared a stale alert latch found at startup")


alert_pin.irq(trigger=Pin.IRQ_FALLING, handler=lambda pin: alert_flag.set())


async def alert_task():
    while True:
        await alert_flag.wait()
        aff, cvrf, ovf = ina.read_alert_flags()  # reading clears AFF, releases the pin
        if aff:
            print(">>> ALERT: current = {:.2f} mA (limit {} mA) <<<".format(
                ina.current_mA, CURRENT_ALERT_MA))
        elif ovf:
            print(">>> ALERT: math overflow flag set - reading out of range <<<")
        # Small debounce: if the current is still over threshold the
        # comparator re-latches (and re-fires the IRQ) on the next
        # conversion, so this just keeps the console readable.
        await asyncio.sleep_ms(200)


async def status_task():
    while True:
        print("bus={:.3f} V  shunt={:.2f} mV  current={:.2f} mA  power={:.1f} mW".format(
            ina.bus_voltage, ina.shunt_voltage * 1000, ina.current_mA, ina.power_mW))
        await asyncio.sleep_ms(STATUS_PERIOD_MS)


def _apply_load_command(cmd):
    """Pure command handler - kept separate from I/O so it's easy to test."""
    cmd = cmd.strip().lower()
    if cmd in ("on", "1"):
        load_pin.value(1)
        print("GPIO{} -> ON".format(LOAD_PIN_NUM))
    elif cmd in ("off", "0"):
        load_pin.value(0)
        print("GPIO{} -> OFF".format(LOAD_PIN_NUM))
    elif cmd in ("toggle", "t"):
        load_pin.value(0 if load_pin.value() else 1)
        print("GPIO{} -> {}".format(LOAD_PIN_NUM, "ON" if load_pin.value() else "OFF"))
    elif cmd in ("status", "s"):
        print("GPIO{} is currently {}".format(LOAD_PIN_NUM, "ON" if load_pin.value() else "OFF"))
    elif cmd in ("help", "h", "?"):
        print("commands: on | off | toggle | status | help")
    elif cmd == "":
        pass
    else:
        print("unrecognised command '{}' (try: on / off / toggle / status)".format(cmd))


async def input_task():
    """
    Non-blocking console reader. Type 'on', 'off', 'toggle' or 'status' and
    press Enter to drive GPIO21.
    """
    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    buf = []
    print("Ready. Commands: on | off | toggle | status | help")
    while True:
        if poll.poll(0):
            ch = sys.stdin.read(1)
            if ch in ("\n", "\r"):
                if buf:
                    _apply_load_command("".join(buf))
                    buf = []
            else:
                buf.append(ch)
        await asyncio.sleep_ms(50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    await asyncio.gather(
        alert_task(),
        status_task(),
        input_task(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        load_pin.value(0)
        ina.disable_alert()
        # asyncio.run() closes the loop; reset it so the script can be
        # re-run from the REPL (e.g. after Ctrl-C) without a stale loop.
        asyncio.new_event_loop()
