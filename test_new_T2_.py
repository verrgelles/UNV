import time
import threading
import queue
from spincore_driver.builder import build_impulses_for_cv_odmr
import numpy as np
from matplotlib import pyplot as plt
import pcapy
from hardware.spincore import SpincoreDriver
from hardware.rigol_rw import RigolDriver
from packets import raw_packet_to_dict
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
def packet_thread(packet_queue, cap,num_probegov):
    def handle_packet(pwk, packet):
        # global packet_queue

        rw = packet[42:]  # обрезаем заголовки(ETH hdr IP hdr UDP hdr)
        k = raw_packet_to_dict(rw)
        #print(k['count_pos'])
        if k.get('flag_pos') == 1:
            packet_queue.put_nowait(k['count_pos'] / num_probegov)

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
    num_probegov = 1
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
    rigol.setup_sweep(gain,start_freq,stop_freq,freq_step)

    build_impulses_for_cv_odmr(count_time=1 * ms)
    # --- Очередь для передачи данных ---
    packet_queue = queue.Queue(maxsize=100000)
    threading.Thread(target=packet_thread, args=(packet_queue,cap,num_probegov), daemon=True).start()
    ph = [0]*len(frequencies)
    for i in range(num_probegov):
        while 1:
            if packet_queue.qsize() >= len(frequencies):
                print(i)
                break
        for c in range(0, len(frequencies)):
            ph[c]+=(packet_queue.get()/num_probegov)

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