from RPi import GPIO


class CommonGPIO:

    LOW = 0
    HIGH = 1

    PULL_UP = GPIO.PUD_UP
    PULL_DOWN = GPIO.PUD_DOWN

    def __init__(self):
        GPIO.setmode(GPIO.BCM)

    def setup_out(self, pin, pull: int = GPIO.PUD_OFF):
        GPIO.setup(pin, GPIO.OUT, pull)

    def setup_in(self, pin, pull: int = GPIO.PUD_OFF):
        GPIO.setup(pin, GPIO.IN, pull)

    def output(self, pin, signal):
        GPIO.output(pin, signal)

    def input(self, pin):
        return GPIO.input(pin)

    def cleanup(self):
        GPIO.cleanup()

