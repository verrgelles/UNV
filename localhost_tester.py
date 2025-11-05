import socket
import struct
import time
import random


def create_udp_packet_simple(packet_counter):
    """Создает простой UDP-пакет для тестирования"""
    parts = []

    # Байт 0: Не используется
    parts.append(b'\x00')

    # Байты 1-2: Счетчик пакетов
    parts.append(struct.pack('>H', packet_counter))

    # Байты 3-4: Не используются
    parts.append(b'\x00\x00')

    # Байт 5: Флаги (случайные)
    import socket
    import struct
    import time
    import random

def create_udp_packet(packet_counter):
    """Создает UDP-пакет согласно структуре"""
    parts = []

    # Байт 0: Не используется
    parts.append(b'\x00')

    # Байты 1-2: Счетчик пакетов
    parts.append(struct.pack('>H', packet_counter))

    # Байты 3-4: Не используются
    parts.append(b'\x00\x00')

    # Байт 5: Флаги
    parts.append(bytes([255]))

    # Байты 6-9: Счетчик фотонов
    parts.append(struct.pack('>I', random.randint(10, 100)))

    # Временные метки канала 1 (6 × 4 байта)
    for _ in range(6):
        parts.append(struct.pack('>I', random.randint(0, 1000000)))

    # Временные метки канала 2 (6 × 4 байта)
    for _ in range(6):
        parts.append(struct.pack('>I', random.randint(0, 1000000)))

    # Счетчики триггеров (по 3 байта)
    parts.append(struct.pack('>I', random.randint(0, 1000))[1:])
    parts.append(struct.pack('>I', random.randint(0, 1000))[1:])

    packet = b''.join(parts)
    #print(f"Создан пакет размером: {len(packet)} байт")
    #print(packet.hex(" "))
    return packet

def send_packets():
    host = "127.0.0.1"
    port = 54321

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Отправка пакетов на {host}:{port}")
    print("Нажмите Ctrl+C для остановки...")

    try:
        counter = 1
        packet = create_udp_packet(counter)
        while True:
            #packet = create_udp_packet(counter)
            sock.sendto(packet, (host, port))
            print(f"Отправлен пакет #{counter}")
            counter += 1
            time.sleep(0.0001)
    except KeyboardInterrupt:
        print("\nОстановлено")
    finally:
        sock.close()

if __name__ == "__main__":
    send_packets()