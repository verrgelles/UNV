from hardware.spincore import impulse_builder
import time
import threading
import queue

import numpy as np
import pcapy
from matplotlib import pyplot as plt
from pyvisa import ResourceManager

from packets import raw_packet_to_dict

# 0 AOM
# 1 Gen imp in
# 2 FPGA
# 3 Generator sweep

t = 5*1E3 #ns
T = 5*1E3 #ns
F = 400 #ns
t_cnt = 2*1E3 #ns
t_ofst = 200 #ns

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
dev.write(":MOD:STAT 1")
dev.write(":PULM:SOUR EXT")
dev.write(":PULM:STAT 1")
dev.write(":OUTP 1")


impulse_builder(
    4,
    [0, 1, 2, 3],
    [2, 1, 2, 1],
    [0, 250+t+T, 375+t, 375+t+T+t_ofst, 375+t+T+t_cnt+F+t_ofst, 375+t+T+2*t_cnt+F+t_ofst],
    [250+t,250+2*t+T, 375+t+T, 375+t+T+t_cnt+t_ofst, 375+t+T+2*t_cnt+F+t_ofst, 375+t+T+2*t_cnt+F+t_ofst+ 5*1E3],
    15,
    int(1),
    int(1E6)
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
        if k.get('flag_pos') == 1:
            if k.get('package_id') % 2 == 0:
                packet_queue.put_nowait(k['count_pos'])

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
dev.write(":MOD:STAT 0")
dev.write(":PULM:STAT 0")
dev.close()

plt.plot(frequencies[2:], ph[2:])
plt.xlabel("Frequency (Hz)")
plt.ylabel("Photon count")
plt.title("Photon count vs Frequency")
plt.grid(True)
plt.show()