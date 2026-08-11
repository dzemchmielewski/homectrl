#!/usr/bin/env python3
"""
Monitor GPIO pins using gpiozero.

Usage:
    python pinmonitor.py <pin1> <pin2> ... <pinN>

Example:
    python pinmonitor.py 17 18 27

Reads N pin numbers (BCM numbering) from the command line, prints the
current value of each, then watches all of them and prints the pin
number and new value whenever one changes state. Press Ctrl+C to stop;
all pins are closed in the finally block regardless of how the script
exits.
"""

import sys
from signal import pause
from gpiozero import DigitalInputDevice


def parse_pins(argv):
    if len(argv) < 2:
        sys.exit(f"Usage: {argv[0]} <pin1> <pin2> ... <pinN>")
    try:
        pins = [int(p) for p in argv[1:]]
    except ValueError:
        sys.exit("Error: all arguments must be integers (GPIO pin numbers).")
    return pins


def make_handler(pin_number, device):
    """Returns a callback that prints the pin number and its new value."""
    def handler():
        print(f"Pin {pin_number} changed -> {int(device.value)}")
    return handler


def main():
    pins = parse_pins(sys.argv)
    devices = {}

    try:
        # Create a DigitalInputDevice for each requested pin.
        # pull_up=False (default) means the pin floats/reads low unless
        # driven high externally. Set pull_up=True below if your wiring
        # needs an internal pull-up resistor instead.
        for pin in pins:
            devices[pin] = DigitalInputDevice(pin)

        print("Initial pin values:")
        for pin, device in devices.items():
            print(f"  Pin {pin}: {int(device.value)}")

        # Register change callbacks for both directions (0->1 and 1->0).
        for pin, device in devices.items():
            device.when_activated = make_handler(pin, device)
            device.when_deactivated = make_handler(pin, device)

        print("\nWatching for changes (Ctrl+C to stop)...")
        pause()  # blocks here, callbacks fire in the background

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        for device in devices.values():
            device.close()
        print("All pins closed.")


if __name__ == "__main__":
    main()