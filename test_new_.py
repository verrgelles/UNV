import pcapy
from packets import raw_packet_to_dict




iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")
#FIXME packet speed
packet_speed = 8000 #p/s

def handle_packet(pwk, packet):

    rw = packet[42:]
    k = raw_packet_to_dict(rw)
    if k['flag_pos'] == 1:
        print("pos", k['flag_pos'])
    if k['flag_neg'] == 1:
        print("neg", k['flag_neg'])

while 1:
    try:
        cap.loop(-1, handle_packet)
    except KeyboardInterrupt:
        pass


