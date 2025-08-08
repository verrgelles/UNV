import time

import numpy as np

from hardware.mirrors import move_to_position, open_serial_port

X = int(input())
Y = int(input())
step = float(input())

dev = open_serial_port()
#center = get_position(dev)
center = [0, 0]
tw = 0.1

try:
    while 1:
        for turn in [0,1,2,3,4]:
            if turn == 0:
                xi = np.arange(start=-X/2+center[0], stop=X/2+center[0]+step, step=step)
                yi = Y/2+center[1]
                for i in xi:
                    move_to_position(dev, [i, yi])
                    time.sleep(tw)
            elif turn == 1:
                xi = X/2+center[0]
                yi = np.arange(start=Y/2+center[1], stop=-(Y/2+center[1]+step), step=-step)
                for i in yi:
                    move_to_position(dev, [xi, i])
                    time.sleep(tw)
            elif turn == 3:
                xi = np.arange(start=X/2+center[0], stop=-(X/2+center[0]+step), step=-step)
                yi = -Y/2+center[1]
                for i in xi:
                    move_to_position(dev, [i, yi])
                    time.sleep(tw)
            elif turn == 4:
                xi = -X / 2 + center[0]
                yi = np.arange(start=-Y/2+center[1], stop=Y/2+center[1]+step, step=step)
                for i in yi:
                    move_to_position(dev, [xi, i])
                    time.sleep(tw)

except KeyboardInterrupt:
    pass