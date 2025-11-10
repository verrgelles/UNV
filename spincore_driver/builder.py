import spincore_driver.spinapi as pb
print("spinapi loaded from:", pb.__file__)
from dataclasses import dataclass
import time


CH0 =0x1
CH1 = 0x1 << 1
CH2 = 0x1 << 2
CH3 = 0x1 << 3
CH4 = 0x1 << 4
CH5 = 0x1 << 5
CH6 = 0x1 << 6
CH7 = 0x1 << 7
CH8 = 0x1 << 8
CH9 = 0x1 << 9
CH10 = 0x1 << 10
CH11 = 0x1 << 11
CH12 = 0x1 << 12
CH13 = 0x1 << 13
CH14 = 0x1 << 14
CH15 = 0x1 << 15
CH16 = 0x1 << 16
CH17 = 0x1 << 17
CH18 = 0x1 << 18
CH19 = 0x1 << 19
CH20 = 0x1 << 20
CH21 = 0x1 << 21
CH22 = 0x1 << 22
CH23 = 0x1 << 223



@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0
def spincore_init():
    if pb.pb_init() != 0:
        print("Init failed:", pb.pb_get_error())
        exit()
    pb.pb_core_clock(500.0)
    pb.pb_set_defaults()
###########################################################
# 4--AOM   3--Gen imp in   0--FPGA T1 2--Generator sweep
#t_laser = 100
#t_dark=5
#t_SVCh = 100
#t_sbor= 5
#t_norm = 5
#CH4 LASER
#CH3 СВЧ
#CH0 ИЗМЕРЕНИЕ
#CH2 SWEEP
def build_impulses_for_imp_odmr(t_laser = 100, t_dark=5, t_SVCh = 100, t_sbor= 5, t_norm = 5):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON|CH4|CH0, pb.CONTINUE, 0, t_norm*pb.us)#Поднимаем лазер и сбор на tnorm
    pb.pb_inst_pbonly(pb.ON|CH4, pb.CONTINUE, 0, (t_laser-t_norm) * pb.us)# доподнимаем лазер
    pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark * pb.us)  # все нули на tdark
    pb.pb_inst_pbonly(pb.ON | CH3, pb.CONTINUE, 0, t_SVCh * pb.us) #СВЧ импульс на t_свч
    pb.pb_inst_pbonly(pb.ON | CH4|CH0, pb.CONTINUE, 0, t_sbor * pb.us)#поднимаем измерения и лазер на t_сбор
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, (t_laser-t_sbor) * pb.us) #еще поднимаем второй лазер на tлазер-tсбор
    pb.pb_inst_pbonly(pb.ON | CH2, pb.CONTINUE, 0,100 * pb.ns)  # дергаем свип
    pb.pb_inst_pbonly(0x00, pb.BRANCH,start,30.0*pb.ms)# пауза 30 мс
    pb.pb_stop_programming()

    # --- Запуск ---

    pb.pb_start()
    #try:
        #time.sleep(100)
    #except:
        #pass
    #finally:
        #pb.pb_stop()
    pb.pb_close()

def build_impulses_rabi(t_laser = 100, t_dark=5, t_sbor= 5, t_norm = 5,begin=1,end=400):
    spincore_init()
    num_points = 500
    time_step = (end - begin ) / num_points
    #top limit 1ms
    print(time_step)
    print("num_points:", num_points)
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(0x00, pb.CONTINUE,0, 5*pb.ms)# пауза 5 мс
    for i in range(num_points):
        pb.pb_inst_pbonly(pb.ON | CH4 | CH0, pb.CONTINUE, 0, t_norm * pb.us)  # Поднимаем лазер и сбор на tnorm
        pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, (t_laser - t_norm) * pb.us)  # доподнимаем лазер
        pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark * pb.us)  # все нули на tdark
        pb.pb_inst_pbonly(pb.ON | CH3, pb.CONTINUE, 0, begin * pb.us + time_step * i * pb.us)  # СВЧ импульс переменной длины
        pb.pb_inst_pbonly(pb.ON | CH4 | CH0, pb.CONTINUE, 0, t_sbor * pb.us)  # поднимаем измерения и лазер на t_сбор
        pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0,(t_laser - t_sbor) * pb.us)  # еще поднимаем второй лазер на tлазер-tсбор
        pb.pb_inst_pbonly(pb.ON | CH2, pb.CONTINUE, 0, 100 * pb.ns)  # дергаем свип
        pb.pb_inst_pbonly(0x00, pb.CONTINUE,0,1*pb.ms)# пауза 1 мс(debug, 20 release)
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 5 * pb.ms)  # пауза 5 мс
    pb.pb_stop_programming()
    print("stopped programming")
    # --- Запуск ---

    pb.pb_start()
    #try:
        #time.sleep(100)
    #except:
        #pass
    #finally:
        #pb.pb_stop()
    pb.pb_close()
def setup_ch4():
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0,  1000*pb.ms)
    pb.pb_inst_pbonly(0, pb.CONTINUE, 0, 500 * pb.ms)
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 0 * pb.ms)
    pb.pb_stop_programming()
    pb.pb_start()
    pb.pb_close()
if __name__ == "__main__":
    build_impulses_rabi(begin=1,end=400)
