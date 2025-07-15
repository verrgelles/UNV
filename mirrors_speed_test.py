import time

import numpy as np
from playsound3 import playsound

from hardware.mirrors import open_serial_port, move_command

dev = open_serial_port()
step = 0.01
array = np.arange(start=1.100, stop=2.100+step, step=step)
print(len(array))
playsound("1.mp3")
t1 = time.time_ns()
for j in array:
    j = float(j)
    move_command(dev, j, j)
    time.sleep(0.5)
t2 = time.time_ns()
playsound("1.mp3")
delta = t2 - t1
print(delta)