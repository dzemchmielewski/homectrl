from max6675 import MAX6675
import time

def main():
    m = MAX6675()
    last = None
    while True:
        value = m.read()
        if value != last:
            t = time.localtime()
            print("{}°C \t {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(value, t[0], t[1], t[2], t[3], t[4], t[5], 0))
            last = value
        time.sleep(1)

if __name__ == "__main__":
    main()
