import time
import machine

for i in range(3, 0, -1):
    print(f"Hard reset in {i} seconds...\r", end='')
    time.sleep(1)
print("Hard reset!")
machine.reset()
