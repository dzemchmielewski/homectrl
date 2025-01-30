from machine import Pin


class SimpleButton:

    def __init__(self, pin: int, active_low=True):
        self.pin = Pin(pin, Pin.IN)
        self.pushed_value = 0 if active_low else 1
        self.pushed_down = False

    def clicked(self):
        value = self.pin.value()
        if value == self.pushed_value:
            self.pushed_down = True
        else:
            if self.pushed_down:
                self.pushed_down = False
                return True
        return False
