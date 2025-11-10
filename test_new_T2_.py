import time
import threading
import queue
import numpy as np
from matplotlib import pyplot as plt
import pcapy
from hardware.spincore import SpincoreDriver
from hardware.rigol_rw import RigolDriver
from packets import raw_packet_to_dict

def plotter(frequencies,ph):
    plt.plot(frequencies[2:], ph[2:])
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Photon count")
    plt.title("Photon count vs Frequency")
    plt.grid(True)
    plt.show()

# --- Поток обработки пакетов ---
def packet_thread(packet_queue, cap,av_pulse):
    def handle_packet(pwk, packet):
        # global packet_queue
        rw = packet[42:]  # обрезаем заголовки(ETH hdr IP hdr UDP hdr)
        k = raw_packet_to_dict(rw)
        if k.get('flag_pos') == 1:
            packet_queue.put_nowait(k['count_pos'] / av_pulse)

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
    av_pulse = 1
    count_time = 1
    num_probegov = 100
    # 10
    shift = 10

    #T1
    start_t = shift + np.arange(av_pulse) * 2 * count_time - 5
    stop_t  = start_t + count_time

    #T2
    start_t = np.append(start_t, 0)
    stop_t = np.append(stop_t, max(stop_t)+3)

    #Gen
    start_t = np.append(start_t, stop_t[-1])
    stop_t = np.append(stop_t, stop_t[-1]+5)
    # --- Настройки ---
    start_freq = 2775 * 1E6
    stop_freq = 2800 * 1E6
    freq_step = 200 * 1E3
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
    spincore=SpincoreDriver()

    start_t=start_t.tolist()
    start_t.append(0)
    stop_t = stop_t.tolist()
    stop_t.append(14)
    print(start_t,stop_t)
    spincore.impulse_builder(
        4,
        [0, 1, 2,4],
        [av_pulse, 1, 1,1],
        start_t,
        stop_t,
        5000,
        int(1E6),
        int(1E3)
    )
    # --- Очередь для передачи данных ---
    packet_queue = queue.Queue(maxsize=100000)
    threading.Thread(target=packet_thread, args=(packet_queue,cap,av_pulse), daemon=True).start()
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
    plotter(frequencies[2:], ph[2:])

if __name__ == "__main__":
    main()