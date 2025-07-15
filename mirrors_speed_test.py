import time

import numpy as np
from hardware.mirrors import open_serial_port, move_command

dev = open_serial_port()
step = 0.2
array = np.arange(start=1.100, stop=1.900+step, step=step)
for j in array:
    print("Start")
    t1 = time.time_ns()
    j = float(j)
    move_command(dev, j, j)
    delta = time.time_ns() - t1
    print("Stop", delta)
    time.sleep(3)