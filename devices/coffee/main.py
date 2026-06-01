if not boot.isconnected():
    # Normal mode - runs application without network
    from coffee import CoffeeApplication
    CoffeeApplication().run()

else:
    # Maintenance mode - webrepl available,
    # no application launched, orange LED shines.
    # Red button turns the LED off
    from machine import Pin
    red_btn = Pin(35, Pin.IN, Pin.PULL_DOWN)
    orange = Pin(26, Pin.OUT)
    orange.on()

    def red_button_pressed(pin):
        orange.off()

    red_btn.irq(handler=red_button_pressed, trigger=Pin.IRQ_FALLING)
