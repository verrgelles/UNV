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