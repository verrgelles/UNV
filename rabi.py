#from hardware.spincore import SpincoreDriver
from spincore_driver.builder import build_impulses_rabi
from hardware.rigol_rw import RigolDriver
import time
import threading
import queue

import numpy as np
import pcapy
from matplotlib import pyplot as plt
from pyvisa import ResourceManager

from packets import raw_packet_to_dict


def plotter(times, ph):
    plt.plot(times[2:], ph[2:])
    plt.xlabel("Time (us)")
    plt.ylabel("Photon count")
    plt.title("Photon count vs Frequency")
    plt.grid(True)
    plt.show()


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


# 0 AOM
# 1 Gen imp in
# 2 FPGA
# 3 Generator sweep


# --- Настройки ---
gain = 10
RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
cap.setfilter("udp and src host 192.168.1.2")


# --- Настройка генератора ---
rigol=RigolDriver()
num_probegov = 3
rigol.setup_rabi(gain = 10,freq=2890 * 1E6)
begin =0.1
end = 3
times = [begin+i*(end-begin)/500 for i in range(500)]
print(times)
build_impulses_rabi(t_laser = 1000, t_dark=5, t_sbor= 100, t_norm = 100,begin = 0.1, end = 3)
# --- Очередь для передачи данных ---
packet_queue_meas = queue.Queue(maxsize=100000)
packet_queue_norm = queue.Queue(maxsize=100000)

# --- Поток обработки пакетов ---
def packet_thread():
    def handle_packet(pwk, packet):
        global packet_queue_meas,packet_queue_norm
        rw = packet[42:]  # обрезаем заголовки
        k = raw_packet_to_dict(rw)
        if k.get('flag_pos') == 1:
            if k.get('package_id') % 2 == 0:
                packet_queue_norm.put_nowait(k['count_pos'])
            else:
                packet_queue_meas.put_nowait(k['count_pos'])


    cap.loop(-1, handle_packet)


threading.Thread(target=packet_thread, daemon=True).start()
ph = [0] * len(times)
for i in range(num_probegov):
    while 1:
        if packet_queue_meas.qsize() >= len(times):
            print(i)
            break
    for c in range(0, len(times)):
        sbor=packet_queue_meas.get()
        norm=packet_queue_norm.get()
        ph[c] += 2*((norm-sbor)/(norm+sbor))

# spincore.stopPb()
# spincore.closePb()
rigol.shutdown_sweep()
rigol.dev.close()

plotter(times, ph)