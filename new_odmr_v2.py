#from hardware.spincore import SpincoreDriver
import spincore_driver.spinapi
from spincore_driver.builder import build_impulses_for_imp_odmr_single,build_impulses_for_imp_odmr_multi
from hardware.rigol_rw import RigolDriver
import time
import threading
import queue
import datetime
import os
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

# --- Настройки ---
start_freq = 2855 * 1E6
stop_freq = 2890 * 1E6
freq_step = 500 * 1E3
gain = 10

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
cap.setfilter("udp and src host 192.168.1.2")

frequencies = np.arange(start=start_freq, stop=(stop_freq + freq_step), step=freq_step)

# --- Настройка генератора ---
rigol=RigolDriver()
rigol.setup_sweep_for_imp_odmr(gain,start_freq,stop_freq,freq_step)
#number_of_measurements=10
num_probegov = 100
#build_impulses_for_imp_odmr_single(t_laser = 100, t_dark=5, t_SVCh = 100, t_sbor= 50, t_norm = 50,delay_between_measurements=50,number_of_measurements=number_of_measurements)
build_impulses_for_imp_odmr_multi(t_laser=10, t_dark=5, t_SVCh=100, t_sbor=10, t_norm=10,t_dark_2=0)#микросекунды
#---------------------Блок настроек-----------------------#


# --- Очередь для передачи данных ---
packet_queue_meas = queue.Queue(maxsize=1000000)
packet_queue_norm = queue.Queue(maxsize=1000000)

# --- Поток обработки пакетов ---
def packet_thread():
    def handle_packet(pwk, packet):
        global packet_queue_meas,packet_queue_norm
        rw = packet[42:]  # обрезаем заголовки
        k = raw_packet_to_dict(rw)
        if k.get('flag_pos') == 1:
            #print(k.get('package_id'))
            if k.get('package_id') % 2 == 0:
                #print("put norm")
                packet_queue_norm.put_nowait(k['count_pos'])
            else:
                #print("put meas")
                packet_queue_meas.put_nowait(k['count_pos'])


    cap.loop(-1, handle_packet)


threading.Thread(target=packet_thread, daemon=True).start()
ph = [0] * len(frequencies)
num=1
'''while 1:
    #if packet_queue_meas.qsize() >= number_of_measurements*len(frequencies):
    if packet_queue_meas.qsize() >=  len(frequencies):
        print(f"measurement number {num} done")
        num+=1
        break
for c in range(0, len(frequencies)):
    for _ in range(number_of_measurements):
        sbor = packet_queue_meas.get()
        norm = packet_queue_norm.get()
        ph[c] += 2*((abs(norm-sbor))/(norm+sbor))'''

for i in range(num_probegov):
    while 1:
        if packet_queue_meas.qsize() >= len(frequencies):
            print(i)
            break
    for c in range(0, len(frequencies)):
        sbor = packet_queue_meas.get()
        norm = packet_queue_norm.get()
        ph[c] += 2 * ((abs(norm - sbor)) / (norm + sbor))

filename = str(datetime.datetime.now())[:-7].replace(":", "-")+".txt"
os.chdir("results_impulse_odmr")
with open(filename, "w") as f:
    f.write(str("Frequency(MHz)    Signal\n",))
    for _ in range(len(frequencies)):
        f.write(f"{(frequencies[_]/1000000):.2f}           {str(ph[_])}\n")
os.chdir("..")
plotter(frequencies, ph)