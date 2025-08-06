import cProfile
import time
import random

import numpy as np
import pandas as pd
import pcapy
import seaborn as sns
from matplotlib import pyplot as plt
import timeit


from hardware.mirrors import open_serial_port, get_position, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict

X = int(input())
Y = int(input())
step = float(input())
time_to_collect = round(int(input())/2) #in ms
assert time_to_collect > 0
print(time_to_collect)

impulse_builder(
                2,
                [0, 2],
                [1, 1],
                [0, 0],
                [time_to_collect, time_to_collect],
                150,
                int(1E6),
                int(1E3)
            )

dev = open_serial_port()
center = [6,-7]
move_to_position(dev, center)
#center = get_position(dev)


xi = np.arange(start=-X/2+center[0], stop=X/2+center[0]+step, step=step)
yi = np.arange(start=Y/2+center[1], stop=-(Y/2-center[1]+step), step=-step) #FIXME перед center[1] поставил - вместо +
#FIXME test
print(yi)
iface = "Ethernet"
#to_ms=время накопления в точке
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")

#FIXME тут меняется скорость
packet_speed = 8000 #packets/s

dt = pd.DataFrame(columns=["x", "y", "ph"])

MAX_COUNT = int(packet_speed*time_to_collect*1E-3)

def handle_packet(pwk, packet):
    global x_t, y_t, packet_count, dt

    packet_count += 1

    if packet_count >= MAX_COUNT:
        raise KeyboardInterrupt()  # Прервать loop, когда достигли лимита

    rw = packet[42:]
    k = raw_packet_to_dict(rw)

    if k['flag_pos'] == 1:
        dt.loc[len(dt)] = {"x": round(x_t, 2), "y": round(y_t,2), "ph": k['count_pos']}


def flush_capture_buffer(capture, flush_time=0.1):
    """
    Прочищает буфер: читает всё, что накопилось, без обработки.
    flush_time — сколько секунд максимум пытаться вычитывать
    """
    start_time = time.time()

    def _flush(_hdr, _data):
        pass  # просто игнорируем

    while True:
        try:
            capture.dispatch(10, _flush)  # читаем максимум 10 пакетов за раз
        except Exception:
            break
        if time.time() - start_time > flush_time:
            break

exit_loop_flag = False

q = time.perf_counter_ns()
for y_t in yi:
    for x_t in xi:
        move_to_position(dev, [x_t, y_t])
        time.sleep(0.03)
        flush_capture_buffer(cap, 0.03)
        packet_count = 0
        try:
            cap.loop(-1, handle_packet)
        except KeyboardInterrupt:
            pass
print((time.perf_counter_ns()-q)*1E-9, "s")
dt = dt.groupby(['x', 'y'], as_index=False)['ph'].mean()
print("Victory")
dev.close()
dt.to_csv("23_7_1_MEAN3.csv") #sum515


heatmap_data = dt.pivot(index='y', columns='x', values='ph')

# 3. Строим heatmap
plt.figure(figsize=(7, 6))
ax = sns.heatmap(heatmap_data, cmap="viridis", cbar_kws={'label': 'Mean ph'})

# Инвертируем ось Y, чтобы (0,0) было внизу, а не вверху
ax.invert_yaxis()

# Подписи и отображение
plt.xlabel("x")
plt.ylabel("y")
plt.tight_layout()
plt.show()
