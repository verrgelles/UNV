import struct
import time
import numpy as np
from collections import deque
from threading import Thread
from queue import Queue, Empty
import pcapy
import matplotlib.pyplot as plt

from hardware.mirrors import open_serial_port
from packets import raw_packet_to_dict_corr

# === Настройки ===
IFACE = "Ethernet"
SRC_FILTER = "udp and src host 192.168.1.2"

MAX_QUEUE_SIZE = 10000
WORKER_COUNT = 8
MAX_PHOTON_HISTORY = 10000

TAU_MAX_NS = 100
BIN_WIDTH_NS = 0.1
NUM_BINS = int(np.round(2 * TAU_MAX_NS / BIN_WIDTH_NS))
BINS = np.linspace(-TAU_MAX_NS, TAU_MAX_NS, NUM_BINS + 1)

packet_queue = Queue(maxsize=MAX_QUEUE_SIZE)
photon_data = deque(maxlen=MAX_PHOTON_HISTORY)
hist_data = np.zeros(NUM_BINS)

# Общие счётчики фотонов
photon_total_1 = 0
photon_total_2 = 0

packet_count = 0

def is_queue_almost_full(q, threshold=0.95):
    return q.qsize() >= int(q.maxsize * threshold)

def handle_packet(hdr, packet):
    global packet_count
    packet_count += 1

    try:
        payload = packet[42:]

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
        except Empty:
            continue
        except Exception as e:
            pass
            #print(f"[✗] Ошибка в packet_worker: {e}")

def correlation_worker():
    global hist_data

    while True:
        try:
            if len(photon_data) < 2:
                continue

            t1_all = [p["tp1_r"] for p in photon_data]
            t2_all = [p["tp2_r"] for p in photon_data]

            photon_data.clear()

            deltas = np.concatenate([
                np.subtract.outer(t1, t2).ravel()
                for t1, t2 in zip(t1_all, t2_all)
            ])

            valid = deltas[(deltas > -TAU_MAX_NS) & (deltas < TAU_MAX_NS)]
            valid = valid[valid != 0]

            if len(valid) == 0:
                raise Exception

            hist, _ = np.histogram(valid, bins=NUM_BINS, range=(-TAU_MAX_NS, TAU_MAX_NS))

            if hist.shape != hist_data.shape:
                #print(f"[!] Пропущен неверный hist: shape={hist.shape}, expected={hist_data.shape}")
                continue

            hist_data += hist

            #print(f"[✓] Гистограмма обновлена. Сумма={np.sum(hist_data):.0f}")

        except Exception as e:
            pass
            #print(f"[✗] Ошибка в correlation_worker: {e}")


def plot_worker():
    global photon_total_1, photon_total_2

    SAVE_INTERVAL = 60  # секунд

    while True:
        time.sleep(SAVE_INTERVAL)

        try:
            if np.sum(hist_data) == 0:
                print("[ℹ] Гистограмма пуста — пропускаем сохранение")
                continue

            #norm_factor = N1 * N2 * BIN_WIDTH_NS
            norm_factor = BIN_WIDTH_NS
            g2_norm = hist_data

            timestamp = int(time.time())
            filename = f"g2_plot_{timestamp}.png"

            plt.figure(figsize=(10, 5))
            plt.bar(BINS[:-1], g2_norm, width=BIN_WIDTH_NS, align='center', edgecolor='blue', alpha=0.7)
            plt.title("g²(τ) нормированная корреляция")
            plt.xlabel("Задержка τ (нс)")
            plt.xlim(-10, 10)
            plt.ylabel("g²(τ)")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(filename)
            print(filename)
            plt.close()

            print(f"[💾] Гистограмма сохранена: {filename}")

        except Exception as e:
            pass
            #print(f"[✗] Ошибка в plot_worker: {e}")


def main():
    #print("[▶] Запуск потоков...")
    det = open_serial_port()
    # FIXME тут ставим координаты
   # move_to_position(det, [-9, 1])

    for _ in range(WORKER_COUNT):
        Thread(target=packet_worker, daemon=True).start()

    Thread(target=correlation_worker, daemon=True).start()
    Thread(target=plot_worker, daemon=True).start()

    cap = pcapy.open_live(IFACE, 106, 0, 0)
    cap.setfilter(SRC_FILTER)

    #print(f"[📡] Захват с интерфейса {IFACE}, фильтр: '{SRC_FILTER}'")
    try:
        cap.loop(-1, handle_packet)
    except KeyboardInterrupt:
        pass
        #print("[⏹] Захват остановлен")

if __name__ == "__main__":
    main()
