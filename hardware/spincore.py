from ctypes import CDLL, POINTER, c_int, c_char_p, create_string_buffer
import os
from hardware.exceptions import SpinCoreConnectionError, SpinCoreExecutionError

# === DLL подключение ===
try:
    dll_path = os.path.abspath('./hardware/spinCoreTest.dll')
    lib = CDLL(dll_path)
except Exception as e:
    raise SpinCoreConnectionError(f"Ошибка загрузки DLL spincore: {e}")

# === Прототипы функций из DLL ===
StrBuild = lib.StrBuild
StrBuild.restype = POINTER(POINTER(POINTER(c_int)))
StrBuild.argtypes = [c_char_p]

setPb = lib.setPb
setPb.restype = c_int
setPb.argtypes = [POINTER(POINTER(POINTER(c_int))), c_int, c_int, c_int]

startPb = lib.pb_S
startPb.restype = c_int

stopPb = lib.pb_R
stopPb.restype = c_int

closePb = lib.pb_C
closePb.restype = c_int


# === Вспомогательные функции ===

def _config_builder(num_channels, channel_numbers, impulse_counts, start_times, stop_times) -> str:
    result = [str(num_channels)]
    start_index = 0
    stop_index = 0

    for i in range(num_channels):
        ch = channel_numbers[i]
        count = impulse_counts[i]
        s_times = start_times[start_index:start_index + count]
        e_times = stop_times[stop_index:stop_index + count]

        result.append(f'_{ch}_{count}')
        result.extend(f'_{t}' for t in s_times + e_times)

        start_index += count
        stop_index += count

    return ''.join(result)


def impulse_builder(num_channels: int,
                    channel_numbers: list[int],
                    impulse_counts: list[int],
                    start_times: list[int],
                    stop_times: list[int],
                    repeat_time: int,
                    pulse_scale: int,
                    rep_scale: int):
    """
    Загружает импульсную программу в SpinCore.

    Args:
        num_channels: число каналов
        channel_numbers: номера каналов
        impulse_counts: число импульсов на каждом
        start_times: список начальных времён импульсов
        stop_times: список конечных времён импульсов
        repeat_time: время повторения (в зависимости от rep_scale)
        pulse_scale: масштаб импульса (1 — нс, 1E3 — мкс, и т.п.)
        rep_scale: масштаб повтора

    Raises:
        SpinCoreExecutionError: при ошибке вызова DLL
    """
    try:
        conf_string = _config_builder(num_channels, channel_numbers, impulse_counts, start_times, stop_times)
        conf_cstr = create_string_buffer(conf_string.encode('utf-8'))
        result = setPb(StrBuild(conf_cstr), repeat_time, pulse_scale, rep_scale)

        if result != 0:
            raise SpinCoreExecutionError(f"Ошибка выполнения setPb: код {result}")

    except Exception as e:
        raise SpinCoreExecutionError(f"Ошибка конфигурации SpinCore: {e}") from e


def start():
    """Запускает выполнение импульсной программы"""
    if startPb() != 0:
        raise SpinCoreExecutionError("Ошибка запуска платы (pb_S)")


def stop():
    """Останавливает выполнение"""
    if stopPb() != 0:
        raise SpinCoreExecutionError("Ошибка остановки платы (pb_R)")


def close():
    """Отключает соединение с платой"""
    if closePb() != 0:
        raise SpinCoreExecutionError("Ошибка закрытия платы (pb_C)")
