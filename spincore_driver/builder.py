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
'''если хотим несколько пробегов'''
def build_impulses_for_imp_odmr_multi(t_laser = 100, t_dark=5, t_SVCh = 100, t_sbor= 5, t_norm = 5,t_dark_2= 1):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON|CH4|CH0, pb.CONTINUE, 0, t_norm*pb.us)#Поднимаем лазер и сбор на tnorm
    pb.pb_inst_pbonly(pb.ON|CH4, pb.CONTINUE, 0, (t_laser-t_norm) * pb.us)# доподнимаем лазер
    pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark * pb.us)  # все нули на tdark
    pb.pb_inst_pbonly(pb.ON | CH3 | CH5, pb.CONTINUE, 0, t_SVCh * pb.us) #СВЧ импульс на t_свч ПЛЮС дублирование на CH3
    pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark_2 * pb.us) # все нули на tdark_2
    pb.pb_inst_pbonly(pb.ON | CH4|CH0, pb.CONTINUE, 0, t_sbor * pb.us)#поднимаем измерения и лазер на t_сбор
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, (t_laser-t_sbor) * pb.us) #еще поднимаем второй лазер на tлазер-tсбор
    pb.pb_inst_pbonly(pb.ON | CH2, pb.CONTINUE, 0,100 * pb.ns)  # дергаем свип
    pb.pb_inst_pbonly(0x00, pb.BRANCH,start,30.0*pb.ms)# пауза 30 мс
    pb.pb_stop_programming()
    print("stopped programming")
    # --- Запуск ---

    pb.pb_start()
    pb.pb_close()
'''один пробег, несколько измерений в точке'''
def build_impulses_for_imp_odmr_single(t_laser = 100, t_dark=5, t_SVCh = 100, t_sbor= 5, t_norm = 5,delay_between_measurements=5,number_of_measurements=20):
    if (number_of_measurements > 500):
        print("Too many measurements:", number_of_measurements)
        return
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, delay_between_measurements * pb.us)  # все нули на tdark
    for i in range(number_of_measurements):
        #print(i)
        pb.pb_inst_pbonly(pb.ON|CH4|CH0, pb.CONTINUE, 0, t_norm*pb.us)#Поднимаем лазер и сбор на tnorm
        pb.pb_inst_pbonly(pb.ON|CH4, pb.CONTINUE, 0, (t_laser-t_norm) * pb.us)# доподнимаем лазер
        pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark * pb.us)  # все нули на tdark
        pb.pb_inst_pbonly(pb.ON | CH3, pb.CONTINUE, 0, t_SVCh * pb.us) #СВЧ импульс на t_свч
        pb.pb_inst_pbonly(pb.ON | CH4|CH0, pb.CONTINUE, 0, t_sbor * pb.us)#поднимаем измерения и лазер на t_сбор
        pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, (t_laser-t_sbor) * pb.us) #еще поднимаем второй лазер на tлазер-tсбор
        pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, delay_between_measurements * pb.us)  # пауза между двумя измерениями

    pb.pb_inst_pbonly(pb.ON | CH2, pb.CONTINUE, 0,100 * pb.ns)  # дергаем свип
    pb.pb_inst_pbonly(0x00, pb.BRANCH,start,30.0*pb.ms)# пауза 30 мс
    pb.pb_stop_programming()
    print("stopped programming")
    # --- Запуск ---

    pb.pb_start()
    pb.pb_close()
def build_impulses_rabi(begin,end,time_step,t_laser = 100, t_dark=5, t_sbor= 5, t_norm = 5,t_dark_2=2):
    spincore_init()
    num_points_max = 500
    num_points=int(round((end-begin)/time_step))
    if num_points_max < num_points+1:
        print(f"Too many points:{num_points}, max number is {num_points_max}")
        exit(1)
    #arr =[]
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(0x00, pb.CONTINUE,0, 5*pb.ms)# пауза 5 мс
    for i in range(num_points+1):
        pb.pb_inst_pbonly(pb.ON | CH4 | CH0, pb.CONTINUE, 0, t_norm * pb.us)  # Поднимаем лазер и сбор на tnorm
        pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, (t_laser - t_norm) * pb.us)  # доподнимаем лазер
        pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark * pb.us)  # все нули на tdark
        pb.pb_inst_pbonly(pb.ON | CH3, pb.CONTINUE, 0, begin * pb.us + time_step * i * pb.us)  # СВЧ импульс переменной длины
        pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark_2 * pb.us)  # все нули на tdark2
        pb.pb_inst_pbonly(pb.ON | CH4 | CH0, pb.CONTINUE, 0, t_sbor * pb.us)  # поднимаем измерения и лазер на t_сбор
        pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0,(t_laser - t_sbor) * pb.us)  # еще поднимаем второй лазер на tлазер-tсбор
        pb.pb_inst_pbonly(0x00, pb.CONTINUE,0,1*pb.ms)# пауза 1 мс(debug, 20 release)
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 1 * pb.ms)  # пауза 5 мс
    pb.pb_stop_programming()
    #print(arr)
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
def build_impulses_for_cv_odmr(count_time=100*pb.us):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)


    start = pb.pb_inst_pbonly(pb.ON | CH3|CH0|CH4, pb.CONTINUE, 0,count_time)#поднимаем лазер, свч и FPGA на count_time
    pb.pb_inst_pbonly(pb.ON | CH2|CH4, pb.CONTINUE, 0,100*pb.ns) #дергаем свип на 100 нс, лазер в единице
    pb.pb_inst_pbonly(pb.ON |CH4, pb.BRANCH, start, 30 * pb.ms) #пауза 30 мс между измерениями, лазер в единице


    pb.pb_stop_programming()
    pb.pb_start()
    pb.pb_close()
def setup_ch4(t_high,t_low):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, t_high)
    #pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0,30 * pb.ms)
    #pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, 30 * pb.us)
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 1.0 * t_low)
    pb.pb_stop_programming()
    print("stopped programming")
    # --- Запуск ---

    pb.pb_start()
    pb.pb_close()
# CH4 LASER
# CH0 ИЗМЕРЕНИЕ
def build_impulses_for_measuring_delays(delay,t_laser=500*pb.ms,t_sbor=5*pb.ms):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, delay)  # поднимаем лазер на время задержки
    pb.pb_inst_pbonly(pb.ON | CH0 | CH4, pb.CONTINUE, 0, t_sbor )  #поднимаем лазер и считывание на t_sbor
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, t_laser-t_sbor-delay)  # доподнимаем лазер до 500 мс
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 5 *  pb.ms)  # все нули
    pb.pb_stop_programming()
    pb.pb_start()
    pb.pb_close()
#CH4 LASER
#CH3 СВЧ
#CH0 ИЗМЕРЕНИЕ
#CH2 SWEEP
def build_odmr_impulses_with_delays(t_laser=1000,delay_between_laser_and_read=600,t_read=100,t_dark=500,t_SVCH=500,delay_between_svch_and_second_laser=100):
    spincore_init()
    pb.pb_start_programming(pb.PULSE_PROGRAM)
    start = pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, delay_between_laser_and_read)  # поднимаем лазер на время задержки(выставления лазерного импульса)
    pb.pb_inst_pbonly(pb.ON | CH0 | CH4, pb.CONTINUE, 0, t_read)  # поднимаем лазер и считывание на t_read
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, t_laser - t_read - delay_between_laser_and_read)  # доподнимаем лазер до t_laser
    pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, t_dark)  # все нули на tdark
    pb.pb_inst_pbonly(pb.ON | CH3, pb.CONTINUE, 0,t_SVCH)  # СВЧ длины t_svch
    pb.pb_inst_pbonly(0x00, pb.CONTINUE, 0, delay_between_svch_and_second_laser)  # все нули на задержку между свч и лазером
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, delay_between_laser_and_read)  # поднимаем второй лазер на время задержки(выставления лазерного импульса)
    pb.pb_inst_pbonly(pb.ON | CH0 | CH4, pb.CONTINUE, 0, t_read)  # поднимаем лазер и считывание на t_read
    pb.pb_inst_pbonly(pb.ON | CH4, pb.CONTINUE, 0, t_laser - t_read - delay_between_laser_and_read)  # доподнимаем лазер до t_laser
    pb.pb_inst_pbonly(0x00, pb.BRANCH, start, 5 * pb.ms)  # все нули
    pb.pb_stop_programming()
    pb.pb_start()
    pb.pb_close()


if __name__ == "__main__":
    #build_impulses_for_imp_odmr_single(t_laser = 100, t_dark=5, t_SVCh = 100, t_sbor= 5, t_norm = 5)
    ms = pb.ms
    ns=pb.ns
    us=pb.us
    #setup_ch4(t_high=500 * ms,t_low=500 * ms)
    #build_impulses_for_measuring_delays(delay=200)
    build_odmr_impulses_with_delays(t_laser=1000*us, delay_between_laser_and_read=600*us, t_read=100*us, t_dark=500*us, t_SVCH=500*us,delay_between_svch_and_second_laser=100*ns)
