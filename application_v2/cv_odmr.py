import time
import threading
import queue
import numpy as np
from matplotlib import pyplot as plt
import pcapy
from pcapy import findalldevs
import pyqtgraph as pg
from hardware.spincore import SpincoreDriver
from hardware.rigol_rw import RigolDriver
from packets import raw_packet_to_dict

def plotter(frequencies,ph,plotwidget):
    plotwidget.plot(frequencies[2:], ph[2:])
    plotwidget.setLabel('bottom', 'Frequency (Hz)', color='green', size='12pt')
    plotwidget.setLabel('left', 'Photon count', color='red', size='12pt')
    #plotwidget.title("Photon count vs Frequency")
    #plotwidget.grid(True)
    #plt.show()

# --- Поток обработки пакетов ---
def packet_thread(packet_queue, cap,av_pulse):
    def handle_packet(pwk, packet):
        # global packet_queue
        rw = packet[32:]  # обрезаем заголовки(ETH hdr IP hdr UDP hdr)
        k = raw_packet_to_dict(rw)
        if k.get('flag_neg') == 1:
            packet_queue.put_nowait(k['count_neg'] / av_pulse)
            # print(k['count_neg'])

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
def do_cv_odmr(start_frequency,stop_frequency,frequency_step,rigol_gain, plotwidget):
    av_pulse = 15
    count_time = 5
    # 10
    shift = 10
    num_iters = 37
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
    start_freq = start_frequency#2860 * 1E6
    stop_freq = stop_frequency #2880 * 1E6
    freq_step = frequency_step
    gain = rigol_gain
    #RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

    iface = "Ethernet"
    #cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
    #cap.setfilter("udp and src host 192.168.1.2")
    ####################
    interfaces = findalldevs()

    if not interfaces:
        print("Не найдены интерфейсы!")
        return

    # В Windows loopback интерфейс часто называется "Adapter for loopback traffic capture"
    # или содержит "loopback". Если не нашли, используем первый интерфейс.
    selected_iface = None
    for iface in interfaces:
        if 'loopback' in iface.lower() or '127.0.0.1' in iface:
            selected_iface = iface
            break

    if not selected_iface:
        selected_iface = interfaces[0]
        print(f"Loopback интерфейс не найден, используем: {selected_iface}")
    else:
        print(f"Используем интерфейс: {selected_iface}")


    # Открываем интерфейс
    cap = pcapy.open_live(selected_iface, 96, 0, 0)
    cap.setfilter("udp")

    #############################################
    frequencies = np.arange(start=start_freq, stop=(stop_freq + freq_step), step=freq_step)
    print(len(frequencies))
    spincore = SpincoreDriver()
    # rigol=RigolDriver()
    spincore.impulse_builder(
        3,
        [0, 3, 8],
        [av_pulse, 1, 1],
        start_t.tolist(),
        stop_t.tolist(),
        5000,
        int(1E6),
        int(1E3)
    )
    # --- Настройка генератора ---
    #rigol.setup_sweep(gain,start_freq,stop_freq,freq_step)
    packet_queue = queue.Queue(maxsize=100000)
    threading.Thread(target=packet_thread, args=(packet_queue, cap, av_pulse), daemon=True).start()
    ph = [0] * len(frequencies)
    for i in range(num_iters):
        while 1:
            if packet_queue.qsize() >= len(frequencies):
                break

        #ph = [0]*len(frequencies)
        for c in range(0, len(frequencies)):
            ph[c]+=(packet_queue.get()/num_iters)

    #dev.write(":OUTP 0")
    #rigol.shutdown_sweep()
    plotter(frequencies[2:], ph[2:],plotwidget)

#if __name__ == "__main__":
    #do_cv_odmr()