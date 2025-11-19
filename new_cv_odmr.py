import time
import threading
import queue
from spincore_driver.builder import build_impulses_for_cv_odmr_v2,build_impulses_for_cv_odmr
import numpy as np
from matplotlib import pyplot as plt
import pcapy
from hardware.spincore import SpincoreDriver
from hardware.rigol_rw import RigolDriver
from packets import raw_packet_to_dict, raw_packet_to_dict_little
import datetime
import os
ns = 1.0
us = 1000.0
ms = 1000000.0
def plotter(frequencies,ph):
    plt.plot(frequencies, ph)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Photon count")
    plt.title("Photon count vs Frequency")
    plt.grid(True)
    plt.show()
# --- Поток обработки пакетов ---
def packet_thread(packet_queue, cap):
    def handle_packet(pwk, packet):
        k = raw_packet_to_dict(packet[42:])# обрезаем заголовки(ETH hdr IP hdr UDP hdr)
        if k.get('flag_pos') == 1:
            packet_queue.put_nowait(k['count_pos'])

    cap.loop(-1, handle_packet)
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
# --- Generate massives ---
def main():
    # --- Настройки ---
    start_freq = 2855 * 1E6
    stop_freq = 2890 * 1E6
    freq_step = 500 * 1E3
    gain = 10
    #RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

    iface = "Ethernet"
    cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
    cap.setfilter("udp and src host 192.168.1.2")

    frequencies = np.arange(start=start_freq, stop=(stop_freq + freq_step), step=freq_step)
    print(len(frequencies))

    # --- Настройка генератора ---
    rigol=RigolDriver()
    rigol.setup_sweep_for_imp_odmr(gain,start_freq,stop_freq,freq_step)
    ####################################################################
    num_average=500
    build_impulses_for_cv_odmr_v2(read_time=10 * ns,num_average=num_average,delay_between_measurements=250*us)
    #####################################################################################
    # --- Очередь для передачи данных ---
    packet_queue = queue.Queue(maxsize=10000000)

    threading.Thread(target=packet_thread, args=(packet_queue,cap), daemon=True).start()
    ph = [0]*len(frequencies)
    ph2 = [0] * len(frequencies)
    sbor_arr=[0] * len(frequencies)
    norm_arr=[0] * len(frequencies)
    while 1:
        if packet_queue.qsize() >= 2*num_average*len(frequencies):
            print("done")
            break
    for c in range(0, len(frequencies)):
        for _ in range(num_average):
            sbor = packet_queue.get()
            norm = packet_queue.get()
            if (norm + sbor == 0):
                continue
            ph[c] += ((abs(sbor - norm)) / (norm + sbor))

            # ph[c]+= sbor/norm
            # sbor_arr[c]+=sbor
            # norm_arr[c]+=norm
        ph[c]= 1 - ph[c]/num_average
    #dev.write(":OUTP 0")
    rigol.shutdown_sweep()
    filename = str(datetime.datetime.now())[:-7].replace(":", "-")+".txt"
    os.chdir("results_cv_odmr")
    with open(filename, "w") as f:
        f.write(str("Frequency(MHz)    Signal\n",))
        for _ in range(len(frequencies)):
            f.write(f"{(frequencies[_]/1000000):.2f}           {str(ph[_])}\n")
    os.chdir("..")
    plotter(frequencies[2:], ph[2:])

if __name__ == "__main__":
    main()