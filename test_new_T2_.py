import time
import threading
import queue

import numpy as np
import pcapy
from matplotlib import pyplot as plt
from pyvisa import ResourceManager
from scipy.special.cython_special import eval_sh_legendre

from hardware.mirrors import open_serial_port, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict
# --- Generate massives ---
av_pulse = 15
count_time = 5
# 10
shift = 10

#T1
start_t = shift + np.arange(av_pulse) * 2 * count_time - 5
stop_t  = start_t + count_time

#T2
start_t = np.append(start_t, 0)
stop_t = np.append(stop_t, max(stop_t)+3)

#Gen
start_t = np.append(start_t, stop_t[-1])
stop_t = np.append(stop_t, stop_t[-1]+5)
print(start_t, stop_t)

# --- Настройки ---
start = 2860 * 1E6
stop = 2880 * 1E6
step = 50 * 1E3
gain = 0
RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
cap.setfilter("udp and src host 192.168.1.2")

frequencies = np.arange(start=start, stop=(stop + step), step=step)
print(len(frequencies))

# --- Настройка генератора ---
rm = ResourceManager()
dev = rm.open_resource(RES)
dev.write(f':SWE:RES')
dev.write(f':LEV {gain}dBm')
dev.write(':SOUR1:FUNC:MODE SWE')
dev.write(":SWE:MODE CONT")
dev.write(":SWE:STEP:SHAP RAMP")
dev.write(":SWE:TYPE STEP")
dev.write(f":SWE:STEP:POIN {len(frequencies)}")
dev.write(f":SWE:STEP:STAR:FREQ {start}")
dev.write(f":SWE:STEP:STOP:FREQ {stop}")
dev.write("SWE:POIN:TRIG:TYPE EXT")
dev.write(":OUTP 1")

"""
- 0 T1
- 3 T2
- 8 Gen
"""


impulse_builder(
    3,
    [0, 3, 8],
    [av_pulse, 1, 1],
    start_t.tolist(),
    stop_t.tolist(),
    5000,
    int(1E6),
    int(1E3)
)

# --- Очистка буфера ---
def flush_capture_buffer(capture, flush_time=0.1):
    start_time = time.time()

    def _flush(_hdr, _data):
        pass

    while True:
        try:
            capture.dispatch(10, _flush)
        except Exception:
            break
        if time.time() - start_time > flush_time:
            break

# --- Очередь для передачи данных ---
packet_queue = queue.Queue(maxsize=100000)

# --- Поток обработки пакетов ---
def packet_thread():
    def handle_packet(pwk, packet):
        global packet_queue
        rw = packet[42:]  # обрезаем заголовки
        k = raw_packet_to_dict(rw)
        if k.get('flag_neg') == 1:
            packet_queue.put_nowait(k['count_neg']/av_pulse)
            #print(k['count_neg'])

    cap.loop(-1, handle_packet)
threading.Thread(target=packet_thread, daemon=True).start()

while 1:
    if packet_queue.qsize() >= len(frequencies):
        break

ph = []
for c in range(0, len(frequencies)):
    if c <= len(frequencies):
        ph.append(packet_queue.get())

    else:
        break
dev.write(":OUTP 0")
plt.plot(frequencies[2:], ph[2:])
plt.xlabel("Frequency (Hz)")
plt.ylabel("Photon count")
plt.title("Photon count vs Frequency")
plt.grid(True)
plt.show()