import time
import threading
import queue
from spincore_driver.builder import build_impulses_for_cv_odmr, build_impulses_for_measuring_delays
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
    plt.xlabel("Delay")
    plt.ylabel("Photon count")
    plt.title("Распределение числа накопленных фотонов по временам задержки")
    plt.grid(True)
    plt.show()

# --- Поток обработки пакетов ---
def packet_thread(packet_queue, cap):
    def handle_packet(pwk, packet):
        # global packet_queue
        rw = packet[42:]  # обрезаем заголовки(ETH hdr IP hdr UDP hdr)
        k = raw_packet_to_dict(rw)
        #print(k['count_pos'])
        if k.get('flag_pos') == 1:
            #print("packet put")
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
    ns = 1.0
    us = 1000.0
    ms = 1000000.0
    iface = "Ethernet"
    cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
    cap.setfilter("udp and src host 192.168.1.2")
    ###------------Блок настроек-------------###
    ###Все времена в наносекундах##############
    start_delay = 100
    stop_delay = 900
    delay_step = 1
    num_captured_photons=100
    ##############################################
    delays=[ i for i in range(start_delay,stop_delay+delay_step,delay_step)]
    values=[0]*len(delays)
    print(delays)
    packet_queue = queue.Queue(maxsize=100000)
    threading.Thread(target=packet_thread, args=(packet_queue, cap), daemon=True).start()
    for i in range(0,len(delays)):
        build_impulses_for_measuring_delays(delay=delays[i]*ns,t_laser=5*ms,t_sbor=1*ms)
        # --- Очередь для передачи данных ---
        #packet_queue = queue.Queue(maxsize=100000)
        #threading.Thread(target=packet_thread, args=(packet_queue,cap), daemon=True).start()
        ph = [0]*num_captured_photons
        while 1:
            if packet_queue.qsize() >= num_captured_photons:
                print("done")
                break
        for c in range(0, num_captured_photons):
            ph[c]=(packet_queue.get())

        print(f"results: {ph}")
        print(f"average:{find_average(ph)}")
        values[i]= find_average(ph)
    plotter(delays, values)
def find_average(mas):
    sum = 0
    for i in range(0,len(mas)):
        sum+=mas[i]
    return sum/len(mas)
if __name__ == "__main__":
    main()