import time

import numpy as np
import pandas as pd

from hardware.mirrors import open_serial_port, get_position, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict

X = int(input())
Y = int(input())
step = int(input())
time_to_collect = int(input())

impulse_builder(
                1,
                [0],
                [1],
                [0],
                [time_to_collect],
                time_to_collect,
                int(1E6),
                int(1E6)
            )

dev = open_serial_port()
center = get_position(dev)

try:
    while 1:
        for turn in [0,1,2,3]:
            if turn == 0:
                xi = np.arange(start=-X/2+center[0], stop=X/2+center[0]+step, step=step)
                yi = Y/2+center[1]
            elif turn == 1:
                xi = X/2+center[0]
                yi = np.arange(start=Y/2+center[1], stop=-Y/2+center[1]+step, step=step)
            elif turn == 3:
                xi = np.arange(start=X/2+center[0], stop=-X/2+center[0]+step, step=step)
                yi = -Y/2+center[1]
            elif turn == 4:
                xi = -X / 2 + center[0]
                yi = np.arange(start=-Y/2+center[1], stop=Y/2+center[1]+step, step=step)

            for i in xi:
                for j in yi:
                    move_to_position(dev,[i, j])
                    time.sleep(0.1)
except KeyboardInterrupt:
    pass

xi = np.arange(start=-X/2+center[0], stop=X/2+center[0]+step, step=step)
yi = np.arange(start=Y/2+center[1], stop=-Y/2+center[1]+step, step=step)

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")

packet_speed = 8000 #packets/s

dt = pd.DataFrame()

def handle_packet(packet):
    global x_t
    global y_t
    rw = packet[42:]
    k = raw_packet_to_dict(rw)
    if k['flag_pos'] == 1:
        dt.loc[len(dt)] = {"x":x_t ,"y":y_t, "ph": k['count_pos']}

for y_t in yi:
    for x_t in xi:
        move_to_position(dev, [x_t, y_t])
        # Задержка для перемещения
        time.sleep(0.03)
        # Начинаем считать фотоны, считаем их время накопления
        # Принимаем лишь необходимое количество пакетов (доп. верификация)
        if cap.loop(int(packet_speed*time_to_collect), handle_packet) == 0:
            # Собрали фотоны
            pass

print(dt)
