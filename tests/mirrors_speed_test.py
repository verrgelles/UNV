import time
import numpy as np
from hardware.mirrors import MirrorsDriver

def test():
    dr = MirrorsDriver()
    step = 0.01
    array = np.arange(start=1.100, stop=2.100+step, step=step)
    print(len(array))
    dr.open_serial_port()
    #start
    t1 = time.time_ns()
    for j in array:
        j = float(j)
        dr.move_command(j, j)
        time.sleep(0.5)
    t2 = time.time_ns()
    #stop
    delta = t2 - t1
    print(delta)
if __name__ == "__main__":
    test()