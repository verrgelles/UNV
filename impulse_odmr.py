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
def plotter(frequencies,ph):
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
rigol=RigolDriver()
spincore=SpincoreDriver()
rigol.setup_sweep_for_imp_odmr(gain,start_freq,stop_freq,freq_step)
num_probegov = 50
t_ch0= 500000 #500 us
T_ch1 = 5000 #5 us
t_ch2 = 3000 #3us
ch2_delay = 4000 #4us
t_raise=250 #ns
rigol_delay = 70 #ns
t_ch3 = 100 #ns
#spincore.startPb()
'''start_times=[0, t_ch0+T_ch1-100, #CH0
     t_ch0-rigol_delay,     #CH1
     t_ch0+T_ch1, t_ch0+T_ch1+t_ch2+ch2_delay, #CH2
     t_ch0+T_ch1+t_ch2+ch2_delay+t_ch2],   #CH3
stop_times=[t_ch0, t_ch0+T_ch1+t_ch0, #CH0
    t_ch0+T_ch1, #CH1
    t_ch0+T_ch1+t_ch2,t_ch0+T_ch1+t_ch2+ch2_delay+t_ch2, #CH2
    t_ch0+T_ch1+t_ch2+ch2_delay+t_ch2+t_ch3], #CH3'''
spincore.impulse_builder(
        num_channels=4,
        channel_numbers=[4, 3, 0, 2],# 4--AOM   3--Gen imp in  1--FPGA T2   0--FPGA T1 2--Generator sweep
        impulse_counts=[2, 1, 1, 1],
        start_times=[0,4001,
                     1000,
                     4000,
                     5000],
        stop_times=[1000,5000,
                    4000,
                    5000,
                    5001],

        repeat_time=30000,       # повтор каждые 30 мс
        pulse_scale=int(1e3),           # 1 us
        rep_scale=int(1e3)            # 1 us
    )




# --- Очередь для передачи данных ---
packet_queue = queue.Queue(maxsize=100000)

# --- Поток обработки пакетов ---
def packet_thread():
    def handle_packet(pwk, packet):
        global packet_queue
        rw = packet[42:]  # обрезаем заголовки
        k = raw_packet_to_dict(rw)
        if k.get('flag_pos') == 1:
            #if k.get('package_id') % 2 == 0:
            packet_queue.put_nowait(k['count_pos'])

        

    cap.loop(-1, handle_packet)
threading.Thread(target=packet_thread, daemon=True).start()
ph = [0]*len(frequencies)
for i in range(num_probegov):
    while 1:
        if packet_queue.qsize() >= len(frequencies):
            break
    for c in range(0, len(frequencies)):
        ph[c]+=(packet_queue.get()/num_probegov)

#spincore.stopPb()
#spincore.closePb()
rigol.shutdown_sweep()
rigol.dev.close()

plotter(frequencies,ph)