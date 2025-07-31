import struct
import time
import numpy as np
from collections import deque
from threading import Thread
from queue import Queue, Empty
import pcapy
import matplotlib.pyplot as plt

from packets import raw_packet_to_dict_corr

IFACE = "Ethernet"
SRC_FILTER = "udp and src host 192.168.1.2"

MAX_QUEUE_SIZE = 1000
WORKER_COUNT = 2
MAX_PHOTON_HISTORY = 10000

TAU_MAX_NS = 100
BIN_WIDTH_NS = 0.1
NUM_BINS = int(np.round(TAU_MAX_NS / BIN_WIDTH_NS))
BINS = np.linspace(-TAU_MAX_NS, TAU_MAX_NS, NUM_BINS + 1)

packet_queue = Queue(maxsize=MAX_QUEUE_SIZE)
photon_data = deque(maxlen=MAX_PHOTON_HISTORY)
hist_data = np.zeros(NUM_BINS - 1)

packet_count = 0

def is_queue_almost_full(q, threshold=0.95):
    return q.qsize() >= int(q.maxsize * threshold)

def handle_packet(hdr, packet):
    global packet_count
    packet_count += 1

    try:
        payload = packet[42:]

        if len(payload) != 64:
            print("[✗] Неверный размер payload (не 64 байта)")
            return

        if is_queue_almost_full(packet_queue):
            print(f"[⚠] Очередь почти заполнена: {packet_queue.qsize()} / {packet_queue.maxsize}")

        packet_queue.put_nowait(payload)

    except Exception as e:
        print(f"[✗] Ошибка обработки пакета: {e}")

def packet_worker():
    while True:
        try:
            payload = packet_queue.get(timeout=1)
            result = raw_packet_to_dict_corr(payload)

            if result.get("flag_valid") == 1:
                photon_data.append(result)
                print(
                    f"[→] Пакет ID={result['package_id']} "
                    f"cnt1={result['cnt_photon_1']:<5} "
                    f"cnt2={result['cnt_photon_2']:<5}"
                )

        except Empty:
            continue
        except Exception as e:
            print(f"[✗] Ошибка в packet_worker: {e}")

def correlation_worker():
    global hist_data

    while True:
        try:
            if len(photon_data) < 2:
                time.sleep(1)
                continue

            t1_all = [p["tp1_r"] for p in photon_data]
            t2_all = [p["tp2_r"] for p in photon_data]

            deltas = np.concatenate([
                np.subtract.outer(t1, t2).ravel()
                for t1, t2 in zip(t1_all, t2_all)
            ])

            valid = deltas[(deltas > -TAU_MAX_NS) & (deltas < TAU_MAX_NS)]

            hist, _ = np.histogram(valid, bins=BINS)
            hist_data += hist

            print(f"[✓] Гистограмма обновлена. Сумма={np.sum(hist_data):.0f}")
            time.sleep(1)

        except Exception as e:
            print(f"[✗] Ошибка в correlation_worker: {e}")
            time.sleep(1)

def plot_worker():
    while True:
        try:
            time.sleep(10)

            if np.sum(hist_data) == 0:
                print("[ℹ] Гистограмма пуста — пропускаем отрисовку")
                continue

            plt.figure(figsize=(10, 5))
            plt.bar(BINS[:-1], hist_data, width=BIN_WIDTH_NS, align='edge', edgecolor='black')
            plt.title("g²(τ) корреляция")
            plt.xlabel("Задержка τ (нс)")
            plt.ylabel("Счёты")
            plt.grid(True)
            plt.tight_layout()
            plt.show(block=False)
            plt.pause(0.1)
            plt.close()

        except Exception as e:
            print(f"[✗] Ошибка в plot_worker: {e}")

def main():
    print("[▶] Запуск потоков...")

    for _ in range(WORKER_COUNT):
        Thread(target=packet_worker, daemon=True).start()

    Thread(target=correlation_worker, daemon=True).start()
    Thread(target=plot_worker, daemon=True).start()

    cap = pcapy.open_live(IFACE, 106, 0, 0)
    cap.setfilter(SRC_FILTER)

    print(f"[📡] Захват с интерфейса {IFACE}, фильтр: '{SRC_FILTER}'")
    try:
        cap.loop(-1, handle_packet)
    except KeyboardInterrupt:
        print("[⏹] Захват остановлен")

if __name__ == "__main__":
    main()
