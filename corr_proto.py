from queue import Queue
from threading import Thread

import pcapy

from packets import raw_packet_to_dict_corr

iface = "Ethernet"
packet_speed = 4000  # packets/second
MAX_COUNT = int(packet_speed * 100 * 1e-3)

cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")

packet_queue = Queue(maxsize=1000)

packet_count = 0

def handle_packet(pwk, packet):
    global packet_count

    packet_count += 1

    if packet_count >= MAX_COUNT:
        raise KeyboardInterrupt()  # Прервать loop, когда достигли лимита

    try:
        rw = packet[42:]  # payload после заголовков Ethernet+IP+UDP
        packet_queue.put_nowait(rw)  # отправляем "сырые данные" в очередь
    except Exception as e:
        print(f"Ошибка при отправке в очередь: {e}")

def packet_worker():
    while True:
        try:
            rw = packet_queue.get(timeout=1)
            k = raw_packet_to_dict_corr(rw)

            if k['flag_valid'] == 1:
                # Обработка валидного пакета
                print(f"[✓] Обработан пакет ID={k['package_id']}")
        except Exception as e:
            # Можно логировать или подавлять при отсутствии пакетов
            continue

def main():
    global packet_count
    packet_count = 0

    # Запускаем 4 потока-обработчика
    for _ in range(4):
        Thread(target=packet_worker, daemon=True).start()

    cap = pcapy.open_live(iface, 106, 0, 0)
    cap.setfilter("udp and src host 192.168.1.2")

    print("Начинаем захват пакетов...")

    try:
        cap.loop(-1, handle_packet)
    except KeyboardInterrupt:
        print("Захват завершён")