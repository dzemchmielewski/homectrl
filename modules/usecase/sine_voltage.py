import math

from machine import Pin, SoftI2C, ADC
from ADS1115 import *
import time


print("START")

# noinspection PyUnreachableCode
if True:
    adc = ADC(Pin(0, mode=Pin.IN))
    adc.atten(ADC.ATTN_11DB)
    adc.width(ADC.WIDTH_12BIT)

if True:
    i2c = SoftI2C(scl=Pin(21), sda=Pin(20), freq=400_000)
    ads = MyADS1115(ADS1115(0x48, i2c=i2c))

def rms(read_function, reads: int = 1000):

    low = 9999999999
    high = -9999999999
    squares = 0
    for _ in range(reads):
        value = read_function()
        squares += value * value
        low = min(value, low)
        high = max(value, high)
    diff = high - low
    rms = math.sqrt(squares / reads)
    print(f"[RMS: {rms:<6.10f}, DIFF PP: {diff:<6.10f}]", end=" ")
    return rms


def peak_to_peak(read_function, reads: int = 1000):
    high, low = peak_to_peak_readings(read_function, reads)
    result = high - low
    print(f"[{result:<6.10f} = {high:<6.10f} - {low:<6.10f}]", end=" ")
    return result

def peak_to_peak_readings(read_function, reads=1000):
    low = high = read_function()
    for _ in range(reads):
        value = read_function()
        low = min(value, low)
        high = max(value, high)
    return high, low

def pp_to_current(vpp_mv: float, mv_per_a: float, zero: float):
    return (vpp_mv - zero) / (2 * mv_per_a * math.sqrt(2))

def gather_pp_values(read_functions: [], expected_amps: []):
    volts_pp = [[], []]
    for amp in expected_amps:
        input(f"Press enter when current {amp} is applied.")
        for index, read_function in enumerate(read_functions):
            values = []
            for i in range(10):
                values.append(peak_to_peak(read_function))
            mean = sum(values) / len(values)
            volts_pp[index].append(mean)
    return volts_pp;

def run():
    #amps = [0, 1.12, 2.44, 3.70, 1.95, 4.32, 6.55]
    # drill:
    amps = [0, 0.75,0.81, 0.825, 0.945]
    # Drill  results: [[28.65095, 81.99622, 94.87803, 110.9846, 154.6735, 154.2422], [22.05063, 108.2657, 128.179, 148.4483, 208.0938, 215.2003]]

    volts_pp = gather_pp_values([lambda: ads.index(0), lambda: ads.index(1)], amps)
    print (f"Gather results: {volts_pp}")
    print ("Analysis:")
    # for sensor in range(2):
    #     zero = volts_pp[sensor][0]
    #     for i in range(1, len(amps)):
    #         print(f"[{sensor}] mV/A: {(volts_pp[sensor][i] - zero) / amps[i]:.10f}")

    print("")

    # for i, Irms in enumerate(amps[1:], start=1):
    #     Vpp = volts_pp[i] - zero         # mV
    #     Ipk = Irms * math.sqrt(2)        # mV/A spec wants DC current
    #     # sensor sensitivity in mV/A:
    #     sens = (Vpp / 2) / Ipk
    #     print(f"{Irms:.2f} A → {sens:.2f} mV/A")


def run2():
    mv_per_a=[54.5, 100]
    zero = [21, 17]
    read_function = adc.read_uv

    try:
        while True:
            currents = [0, 0]
            for i in range(2):
                print(f"{i} -> ", end="")
                adc.setCompareChannels(ADS1115_COMP_0_GND + (i * 0x1000))
                vpp_mv = peak_to_peak(read_function)
                current = pp_to_current(vpp_mv, mv_per_a[i], zero[i])
                print(f" A: {current:.10f}")
                currents[i] = current
            print(f"A: {currents}")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("EXIT")


def linear_interpolate(x_points, y_points, x):
    points = sorted(zip(x_points, y_points))

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]

        if x0 <= x <= x1:
            # Linear interpolation formula
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    # If x is out of bounds, extrapolate
    if x < points[0][0]:
        x0, y0 = points[0]
        x1, y1 = points[1]
    else:
        x0, y0 = points[-2]
        x1, y1 = points[-1]

    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def cubic(x, a, b, c, d):
    return a * x**3 + b * x**2 + c * x + d

def y(x):
    # WCS1800
    # return cubic(x, 4.89441552e-10, -1.29953835e-06, 7.02693021e-03, 8.28240267e-03)
    # ACS712:
    return cubic(x, 9.89674026e-11, -3.92747278e-07, 4.73336328e-03, 7.69959665e-02)


# WCS1800
#vpps = [18.11301, 177.9428, 360.311, 533.8663, 317.4659, 699.8464, 1052.788, 81.99622, 94.87803, 110.9846, 154.6735]
# ACS712:
vpps = [14.83164, 235.7323, 513.3156, 767.0297, 445.1949, 975.7985, 1480.301, 108.2657, 128.179, 148.4483, 208.0938]

amps = [0, 1.12, 2.44, 3.70, 1.95, 4.32, 6.55, 0.75,0.81, 0.825, 0.945]

def z(x):
    return linear_interpolate(vpps, amps, x)

def t(x):
    return x / (2*math.sqrt(2) * 1000)

def run8():
    for i, x in enumerate(vpps):
        print(f" Expected: {amps[i]:.10f}, Calculated: {t(x):.10f}")

def run9():
    def fread():
        return ads.index(1)
    def espread():
        return adc.read_uv() / 1_000

    try:
        while True:
            print(f"A: {z(rms(fread)):.10f}")
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("EXIT")

def run10():
    try:
        while True:
            ads.read_ac()
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("EXIT")


run10()
