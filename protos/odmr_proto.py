import numpy as np
import struct

import pcapy

from hardware.mirrors import open_serial_port, move_to_position
from hardware.spincore import impulse_builder
import time
import matplotlib.pyplot as plt

from pyvisa import ResourceManager

import logging

from packets import raw_packet_to_dict

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

RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"
# Настройка частоты и мощности dbm
start = 2840 * 1E6
stop = 2900 * 1E6
step = 200 * 1E3
# Мощность dbm
gain = 10
# Время накопления
time_to_collect = round(int(input())/2) #in ms
assert time_to_collect > 0
print(time_to_collect)
# Количество усреднений
n_avg = 200

# Название
filename = "file"
assert n_avg > 0

rm = ResourceManager()
dev = rm.open_resource(RES)
dev.write(f':LEV {gain}dBm')
dev.write(":OUTP 1")

impulse_builder(
    2,
    [0, 1],
    [1, 1],
    [0, 0],
    [time_to_collect, time_to_collect],
    150,
    int(1E6),
    int(1E3)
)

frequencies = np.arange(start=start, stop=(stop + step), step=step)
ph = np.zeros(len(frequencies))

ph_tmp = []
c = 0
det = open_serial_port()
#FIXME тут ставим координаты
move_to_position(det, [-1.6,-5.8])

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")
#FIXME packet speed
packet_speed = 8000 #p/s

MAX_COUNT = int(packet_speed*time_to_collect*1E-3)

def handle_packet(pwk, packet):
    global ph_tmp, packet_count

    packet_count += 1

    if packet_count >= MAX_COUNT:
        raise KeyboardInterrupt()  # Прервать loop, когда достигли лимита

    rw = packet[42:]
    k = raw_packet_to_dict(rw)

    if k['flag_valid'] == 1 and k['flag_pos'] == 1:
        ph_tmp.append(k['count_pos'])

q = time.perf_counter_ns()
for n in range(n_avg + 1):
    print(f"Усреднение {n}/{n_avg}")
    for freq in frequencies:
        dev.write(f':FREQ {freq}')
        # time.sleep(0.005)
        time.sleep(0.01)
        tr_freq = int(dev.query(":FREQ?")[:-4])
        if freq == tr_freq:
            # freqw.append(dev.query(":FREQ?"))
            flush_capture_buffer(cap, 0.03)
            packet_count = 0
            try:
                cap.loop(-1, handle_packet)
            except KeyboardInterrupt:
                pass

            try:
                ph[c] += round(sum(ph_tmp) / len(ph_tmp))
            except Exception:
                pass

            ph_tmp = []
            c += 1
        else:
            pass
    c = 0
    if n == n_avg:
        ph = [ph[i] / n_avg for i in range(len(ph))]
print("Time (s):", (time.perf_counter_ns()-q)*1E-9)
dev.write(":OUTP 0")
dev.close()
plt.plot(frequencies[1:], ph[1:])
plt.show()

with open(f'data/{filename}.csv', 'w') as file:
    file.writelines(f"{ph[i + 1]}\n" for i in range(len(ph) - 1))

