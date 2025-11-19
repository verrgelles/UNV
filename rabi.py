#from hardware.spincore import SpincoreDriver
from spincore_driver.builder import build_impulses_rabi_v2
from hardware.rigol_rw import RigolDriver
import time
import threading
import queue
import datetime
import numpy as np
import pcapy
from matplotlib import pyplot as plt
from pyvisa import ResourceManager
import os
from packets import raw_packet_to_dict


def plotter(times, ph):
    plt.scatter(times, ph)
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
ns = 1.0
us = 1000.0
ms = 1000000.0

# --------------------------------- Блок настроек ----------------------------------------№
rigol=RigolDriver()
num_probegov = 10000
rigol.setup_rabi(gain = 10,freq=2773 * 1E6)
begin = 0
end = 1.5
time_step = 0.015
times = [begin+i*time_step for i in range(1+int(round((end-begin)/time_step)))]
print(times)
#build_impulses_rabi(t_laser = 100, t_dark=5, t_sbor= 5, t_norm = 5,begin = begin, end = end,time_step=time_step,t_dark_2=2)
build_impulses_rabi_v2(begin=10 * ns, end=1.5 * us, time_step=0.015 * us, t_laser=100 * us,delay_between_laser_and_read=200 * ns, t_read=5 * us, t_dark=2 * us, delay_between_svch_and_second_laser=1 * us)

#####################################################################################################
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
        if(norm+sbor==0):
            continue
        ph[c] += 2 * (abs((sbor - norm)) / (norm + sbor))

# spincore.stopPb()
# spincore.closePb()
rigol.shutdown_sweep()
rigol.dev.close()
os.chdir("results_rabi")
filename=str(datetime.datetime.now())[:-7].replace(":","-")+".txt"
with open(filename,"w") as f:
    f.write("Time(us)    Signal\n")
    for _ in range(len(times)):
        f.write(f"{str(times[_])}         {str(ph[_])}\n")
os.chdir("..")
plotter(times, ph)