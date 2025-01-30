from machine import Pin, ADC
import time

print("START")

# pin = 0
pin = 4
adc_pin = Pin(pin, mode=Pin.IN)
adc = ADC(adc_pin)
adc.atten(ADC.ATTN_11DB)

def run():
    try:
        while True:
            print(f"UV: {adc.read_uv() / 1_000_000}, range 0-65535: {adc.read_u16()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("EXIT")


run()
