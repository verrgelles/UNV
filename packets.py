import struct

import numpy as np
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
        count_neg = int.from_bytes(payload[61:64], byteorder="little")

        result = {
            "package_id": package_id,
            "flag_valid": flag_valid,
            "flag_neg": flag_neg,
            "flag_pos": flag_pos,
            "count_pos": count_pos,
            "count_neg": count_neg
        }

    return result

def raw_packet_to_dict_corr(payload: bytes):
    if len(payload) != 64:
        raise ValueError('Payload must be 64 bytes')
    else:
        package_id = struct.unpack('<H', payload[1:3])[0]

        byte6 = struct.unpack('<B', payload[5:6])[0]
        flag_valid = byte6 & 0x1
        flag_100ms = byte6 & 0x7

        cnt_photon = struct.unpack('<I', payload[6:10])[0]

        tp1 = [int.from_bytes(payload[10 + 4 * i:14 + 4 * i], byteorder="little") for i in range(0, 5 + 1)]
        tp1_a = [np.round((tp1[i] & 0x1F) * 0.18, 1) for i in range(len(tp1))]  # ns
        tp1_b = [np.round((tp1[i] >> 7) * 5, 1) for i in range(len(tp1))]  # ns
        tp1_r = [(tp1_a[i] + tp1_b[i]) for i in range(len(tp1_a))]  # ns

        tp2 = [int.from_bytes(payload[34 + 4 * i:38 + 4 * i], byteorder="little") for i in range(0, 5 + 1)]
        tp2_a = [np.round((tp2[i] & 0x1F) * 0.18, 1) for i in range(len(tp2))]  # ns
        tp2_b = [np.round((tp2[i] >> 7) * 5, 1) for i in range(len(tp2))]  # ns
        tp2_r = [(tp2_a[i] + tp2_b[i]) for i in range(len(tp2_a))]  # ns

        # Восстановление отдельных счётов
        if package_id % 2 == 0:
            cnt_photon_1 = 0
            cnt_photon_2 = cnt_photon
        else:
            cnt_photon_1 = cnt_photon
            cnt_photon_2 = 0

        result = {
            "package_id": package_id,
            "flag_valid": flag_valid,
            "cnt_photon_1": cnt_photon_1,
            "cnt_photon_2": cnt_photon_2,
            "tp1_r": tp1_r,
            "tp2_r": tp2_r,
            "flag_100ms": flag_100ms
        }

    return result

def raw_packet_to_dict_corr_OLD(payload: bytes):
    if len(payload) != 64:
        raise ValueError('Payload must be 64 bytes')
    else:
        package_id = struct.unpack('<H', payload[1:3])[0]

        byte6 = struct.unpack('<B', payload[5:6])[0]
        flag_valid = byte6 & 0x1
        flag_100ms = byte6 & 0x7

        cnt_photon_1 = struct.unpack('<H', payload[6:8])[0]
        cnt_photon_2 = struct.unpack('<H', payload[8:10])[0]

        tp1 = [int.from_bytes(payload[10 + 4 * i:14 + 4 * i], byteorder="little") for i in range(0, 5 + 1)]
        tp1_a = [np.round((tp1[i] & 0x1F) * 0.18, 1) for i in range(len(tp1))]  # ns
        tp1_b = [np.round((tp1[i] >> 7) * 5, 1) for i in range(len(tp1))]  # ns
        tp1_r = [(tp1_a[i] + tp1_b[i]) for i in range(len(tp1_a))]  # ns

        tp2 = [int.from_bytes(payload[34 + 4 * i:38 + 4 * i], byteorder="little") for i in range(0, 5 + 1)]
        tp2_a = [np.round((tp2[i] & 0x1F) * 0.18, 1) for i in range(len(tp2))]  # ns
        tp2_b = [np.round((tp2[i] >> 7) * 5, 1) for i in range(len(tp2))]  # ns
        tp2_r = [(tp2_a[i] + tp2_b[i]) for i in range(len(tp2_a))]  # ns

        # Восстановление отдельных счётов


        result = {
            "package_id": package_id,
            "flag_valid": flag_valid,
            "cnt_photon_1": cnt_photon_1,
            "cnt_photon_2": cnt_photon_2,
            "tp1_r": tp1_r,
            "tp2_r": tp2_r,
            "flag_100ms": flag_100ms
        }

    return result