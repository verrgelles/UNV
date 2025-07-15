import struct

import pcapy

def raw_packet_to_dict(payload: bytes):
    if len(payload) != 64:
        raise ValueError('Payload must be 64 bytes')
    else:
        package_id = struct.unpack('<H', payload[1:3])[0]
        byte6 = struct.unpack('<B', payload[5:6])[0]
        flag_valid = byte6 & 0x1
        flag_pos = (byte6 & 0x10) >> 4
        flag_neg = (byte6 & 0x8) >> 3
        count_pos = int.from_bytes(payload[58:61], byteorder="little")
        count_neg = int.from_bytes(payload[61:63], byteorder="little")

        result = {
            "package_id": package_id,
            "flag_valid": flag_valid,
            "flag_neg": flag_neg,
            "flag_pos": flag_pos,
            "count_neg": count_neg,
            "count_pos": count_pos
        }
    return result

def packet_callback(packet):
    if packet.haslayer("Raw"):
        payload = bytes(packet["Raw"].load)[42:]
        try:
            result = raw_packet_to_dict(payload)
            if result['flag_pos'] == 1 or result['flag_neg'] == 1:
                return result
            else:
                return None
        except Exception as e:
            return None
    return None


# Выбрать вручную нужный интерфейс
devs = pcapy.findalldevs()

"""print("Интерфейсы:")
for i, d in enumerate(devs):
    print(f"{i}: {d}")"""

print(devs[6])
iface = devs[6]

"""# Открыть интерфейс
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")

prev = 0

# Обработка пакета
def handle_packet(hdr, packet):
    global prev
    rw = packet[42:]
    k = raw_packet_to_dict(rw)
    print(k)

# Цикл захвата
cap.loop(0, handle_packet)  # 0 = бесконечно"""