import time
import numpy as np
from hardware.mirrors import MirrorsDriver

def main():
    X = int(input())
    Y = int(input())
    step = float(input())
    center = [0, 0]
    tw = 0.1
    try:
        dr = MirrorsDriver()
        dr.open_serial_port()
    except Exception as e:
        print(e)
        return

    try:
        while 1:
            for turn in [0,1,2,3,4]:
                if turn == 0:
                    xi = np.arange(start=-X/2+center[0], stop=X/2+center[0]+step, step=step)
                    yi = Y/2+center[1]
                    for i in xi:
                        dr.move_to_position([i, yi])
                        time.sleep(tw)
                elif turn == 1:
                    xi = X/2+center[0]
                    yi = np.arange(start=Y/2+center[1], stop=-(Y/2+center[1]+step), step=-step)
                    for i in yi:
                        dr.move_to_position([xi, i])
                        time.sleep(tw)
                elif turn == 3:
                    xi = np.arange(start=X/2+center[0], stop=-(X/2+center[0]+step), step=-step)
                    yi = -Y/2+center[1]
                    for i in xi:
                        dr.move_to_position([i, yi])
                        time.sleep(tw)
                elif turn == 4:
                    xi = -X / 2 + center[0]
                    yi = np.arange(start=-Y/2+center[1], stop=Y/2+center[1]+step, step=step)
                    for i in yi:
                        dr.move_to_position([xi, i])
                        time.sleep(tw)

    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
