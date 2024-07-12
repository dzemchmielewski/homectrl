from RPi import GPIO


class CommonGPIO:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)

    def setup_out(self, pin):
        GPIO.setup(pin, GPIO.OUT)

    def setup_in(self, pin):
        GPIO.setup(pin, GPIO.IN)

    def output(self, pin, signal):
        GPIO.output(pin, signal)

    def input(self, pin):
        return GPIO.input(pin)

    def cleanup(self):
        GPIO.cleanup()

