from ctypes import CDLL, POINTER, c_int, c_char_p, create_string_buffer
import os
from dataclasses import dataclass
#@dataclass
#class SpincoreInitStruct:
    #def __init__(self):
class SpincoreDriver:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(current_dir, '..', 'shared', 'SpinCore', 'build', 'bin', 'Release', 'SpinCore.dll')
        self.lib = CDLL(dll_path)
        #print(lib._name) #for debugging purposes


        '''Функция создания 3-х мерного массива Data для дальнейшей передачи в функцию setPB()
        * Состав [N_Channels, [Channel, N_Pulses, [T_start], [T_end]], ...]
        * N_Channels - количество задействованых каналов.
        * Массивы из 4 элементов в количестве N_channels штук:
        * 1. Channel - номер канала
        * 2. N_Pulses - количество импульсов в пакете
        * 3. Массив времен начала импульсов
        * 4. Массив времен конца импульсов
        * Данные заполняются в строчку согласно списку выше. Функция сама распределяет элементы строки в подмассивы
        *
        * @*str строка с данными для заполнения массива
        * @return ***Data - тройной указатель на массив
        */'''
        self.StrBuild = self.lib.StrBuild
        self.StrBuild.restype = POINTER(POINTER(POINTER(c_int)))
        self.StrBuild.argtypes = [c_char_p]

        '''* Функция загрузки в плату импульсной последовательности и запуска
        * @***Data - 3х мерный массив датасета импульсной последовательности
        * @repeat - время между концом и началом нового повторения импульсной последовательности
        * @pulseTime, repTime - размерные множители времени. 1 - ns, 1e3 - us, 1e6 - ms, 1e9 - ns
        * @return 0 - успешный пуск. -1 - ошибка'''
        self.setPb = self.lib.setPb
        self.setPb.restype = c_int
        self.setPb.argtypes = [POINTER(POINTER(POINTER(c_int))), c_int, c_int, c_int] #Data, repeat, pulseTime, repTime

        '''/*
        * Функция создания PWM последовательностей. Не используется. Будет либо удалена, либо полностью переработана
        * 
        * Функция создающая массив для функции setPb, представляет собой сборку массива для многоканальной ШИМ модуляции
        * @int N - число рабочих каналов
        * @int arr[][4] - массив характеристик [][0] - номер рабочего канала [0][1] - Период, [0][2] Коэф заполнения в %, [0][3] сдвиг фазы.
        * @int time - размероность времени ms, us, ns
        *
        */'''

        self.pdPWM = self.lib.pb_PWM
        self.pdPWM.restype = c_int
        self.pdPWM.argtypes = [c_int, POINTER(POINTER(c_int)), c_int]

        '''/*
        * Функция открытия (инициализации платы)
        * @return 0 - успех, -1 - ошибка
        */'''
        self.startPb = self.lib.pb_S
        self.startPb.restype = c_int

        ''' 
         * Stops the output of board and resets the PulseBlaster Core. Analog output will 
         * return to ground, and TTL outputs will either remain in the same state they were 
         * in when the reset command was received or return to ground. This also resets the
         * PulseBlaster Core so that the board can be run again using pb_start() or a hardware
         * trigger.  Note: Either pb_reset() or pb_stop() must be called before pb_start() if
         * the pulse program is to be run from the beginning (as opposed to continuing from a
         * WAIT state).
         * @return A negative number is returned on failure. 0 is returned on success.'''
        self.stopPb = self.lib.pb_R
        self.stopPb.restype = c_int


        ''' * End communication with the board. This is generally called as the last line in a program.
         * Once this is called, no further communication can take place with the board
         * unless the board is reinitialized with pb_init(). However, any pulse program that
         * is loaded and running at the time of calling this function will continue to
         * run indefinitely.
         *
         * @return A negative number is returned on failure. 0 is returned on success.'''
        self.closePb = self.lib.pb_C
        self.closePb.restype = c_int


    def _config_builder(self, num_channels, channel_numbers, impulse_counts, start_times, stop_times):
        result = [str(num_channels)]

        start_index = 0
        stop_index = 0

        for i in range(num_channels):
            channel = channel_numbers[i]
            num_impulses = impulse_counts[i]

            channel_start_times = start_times[start_index:start_index + num_impulses]
            channel_stop_times = stop_times[stop_index:stop_index + num_impulses]

            start_index += num_impulses
            stop_index += num_impulses

            result.append(f'_{channel}_{num_impulses}')
            result.extend(f'_{time}' for time in channel_start_times + channel_stop_times)
        print(''.join(result))
        return ''.join(result)


    def impulse_builder(self, num_channels: int, channel_numbers: list[int], impulse_counts: list[int], start_times: list[int],stop_times: list[int], repeat_time, pulse_scale, rep_scale):
        # pulse_scale, rep_scale 1- нс, 1E3 мкс ...
        self.setPb(
            self.StrBuild(create_string_buffer(self._config_builder(num_channels, channel_numbers, impulse_counts, start_times, stop_times).encode("utf-8"))),
            repeat_time,
            pulse_scale,
            rep_scale)


    def impulse_builder_Cold(self, num_channels: int, channel_numbers: list[int], impulse_counts: list[int], start_times: list[int],stop_times: list[int], repeat_time, pulse_scale, rep_scale):
        # pulse_scale, rep_scale 1- нс, 1E3 мкс ...
        self.setPb(
             self.StrBuild(create_string_buffer(self. _config_builder(num_channels, channel_numbers, impulse_counts, start_times, stop_times).encode("utf-8"))),
            repeat_time,
            pulse_scale,
            rep_scale)

if(__name__ == "__main__"):
    dr = SpincoreDriver()
    dr.impulse_builder(1, [0], [1], [0], [10], 10, 1, 1)
