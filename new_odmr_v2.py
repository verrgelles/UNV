from hardware.spincore import SpincoreDriver
from hardware.rigol_rw import RigolDriver
import time
import threading
import queue

import numpy as np
import pcapy
from matplotlib import pyplot as plt
from pyvisa import ResourceManager

from packets import raw_packet_to_dict


def plotter(frequencies, ph):
    plt.plot(frequencies[2:], ph[2:])
    plt.xlabel("Frequency (Hz)")
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
start_freq = 2850 * 1E6
stop_freq = 2890 * 1E6
freq_step = 200 * 1E3
gain = 10
RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
cap.setfilter("udp and src host 192.168.1.2")

frequencies = np.arange(start=start_freq, stop=(stop_freq + freq_step), step=freq_step)
print(len(frequencies))
# --- Настройка генератора ---
# rigol=RigolDriver()
spincore = SpincoreDriver()
#---------------------Блок настроек-----------------------#
#---------------Все времена в микросекуднах---------------#
num_probegov = 50
t_laser = 100
t_dark=5
t_SVCh = 100
t_sbor= 5
t_norm = 5
###########################################################
# 4--AOM   3--Gen imp in  1--FPGA T2   0--FPGA T1 2--Generator sweep
laser1_begin=0
laser1_end = t_laser
laser2_begin = t_laser+t_dark+t_SVCh
laser2_end = laser2_begin+t_laser
laser3_begin = t_laser+t_dark+t_SVCh+t_laser+t_dark
laser3_end = laser3_begin+t_laser

SVCh_begin=t_laser+t_dark
SVCh_end=SVCh_begin+t_SVCh

FPGA1_begin =t_laser+t_dark+t_SVCh
FPGA1_end = FPGA1_begin + t_sbor
spincore.impulse_builder(
    num_channels=3,
    channel_numbers=[4,3,0],#2],
    impulse_counts=[3,1,1],# 1,2,1],
    start_times=[laser1_begin,laser2_begin,laser3_begin,
                 SVCh_begin,
                 FPGA1_begin],
    stop_times=[laser1_end,laser2_end,laser3_end,
                SVCh_end,
                FPGA1_end],
    repeat_time=30000,  # 30 мс
    pulse_scale=int(1e3),         # 1 us
    rep_scale=int(1e3)            # 1 us
)
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
ph = [0] * len(frequencies)
for i in range(num_probegov):
    while 1:
        if packet_queue_meas.qsize() >= len(frequencies):
            break
    for c in range(0, len(frequencies)):
        ph[c] += (packet_queue_meas.get()/ (packet_queue_norm.get()* num_probegov))

# spincore.stopPb()
# spincore.closePb()
# rigol.shutdown_sweep()
# rigol.dev.close()

plotter(frequencies, ph)