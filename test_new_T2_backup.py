import pcapy
import numpy as np
from hardware.spincore import impulse_builder
from matplotlib import pyplot as plt
from packets import raw_packet_to_dict_corr
from packets import raw_packet_to_dict_corr_OLD
import time
from packets import raw_packet_to_dict
# --- Generate massives ---
# --- Generate massives ---
av_pulse = 3
count_time = 5
#die_t = 5
start_t = np.arange(start=count_time, stop=(count_time+count_time*2*(av_pulse)), step=count_time*2)
start_t = np.append(start_t,int(0))
stop_t = np.arange(start=count_time*2,stop=count_time*2*(av_pulse+1), step=count_time*2)
stop_t = np.append(stop_t,stop_t[-1]+count_time)
start_t = np.append(start_t,stop_t[-1]-5)
stop_t = np.append(stop_t,stop_t[-1])
print(f"{start_t}\n{stop_t}")
#impulse_builder(
 #   3,
 #   [0, 3, 8],
  #  [av_pulse, 1, 1],
 #   start_t.tolist(),
  #  stop_t.tolist(),
 #   5000,
  #  int(1E6),
  #  int(1E3)
#)


iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)
cap.setfilter("udp and src host 192.168.1.2")
#FIXME packet speed
packet_speed = 8000 #p/s

count = 0
total = 0
c_l = 0
c_m = 0
c_e = 0
total_a = []
total_t = 0
total_pos = 0
def handle_packet(pwk, packet):
    global count
    global total
    global c_m
    global c_l
    global c_e
    global total_t
    global total_pos
    rw = packet[42:]
    k = raw_packet_to_dict(rw)
    if k['flag_pos'] == 1:
        total += k['count_pos']
        total_pos += k['count_pos']
        #print(f"pos {k['count_pos']}")
    if k['flag_neg'] == 1:
        count+=1
        if total < k['count_neg']:
            c_m+=1
        elif total > k['count_neg']:
            c_l+=1
        else:
            c_e+=1
        total_t += k['count_neg']
        total_a.append(k['count_neg'])
        total = 0
        #print("neg",datetime.datetime.now().time())
    if count >= 500:
        print(f"More: {c_m}\nLess: {c_l}\nEqual: {c_e}\nTotalPos: {total_pos}\nTotalNeg: {total_t}")
        raise KeyboardInterrupt()


local_c = 0
def handle_packet2(pwk, packet):
    global count
    global total
    global c_m
    global c_l
    global c_e
    global total_t
    global total_pos
    global local_c
    rw = packet[42:]
    k = raw_packet_to_dict_corr_OLD(rw)
    print(k["cnt_photon_1"], k["cnt_photon_2"])

try:
    cap.loop(-1, handle_packet2)
except KeyboardInterrupt:
    pass



counter = []
for i in range(len(total_a)):
    counter.append(i)
plt.plot(counter,total_a )
plt.xlabel("packet Num")
plt.ylabel("Photon count")
plt.title("Photon count")
plt.grid(True)
plt.show()