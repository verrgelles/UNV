from pyvisa import ResourceManager
from hardware.exceptions import SignalParameterError, SignalConnectionError

RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

def _open_device():
    try:
        rm = ResourceManager()
        return rm.open_resource(RES)
    except Exception as e:
        raise SignalConnectionError(f"Не удалось открыть подключение к генератору: {e}") from e

def _check_freq_range(freq: float):
    if not (9e3 <= freq <= 13.6e9):
        raise SignalParameterError("Частота должна быть в диапазоне 9 kHz – 13.6 GHz")

def _check_gain_range(gain: int):
    if not (-130 <= gain <= 27):
        raise SignalParameterError("Усиление должно быть в диапазоне [-130, 27] дБм")

def setup_rabi(gain: int, freq: float):
    _check_gain_range(gain)
    _check_freq_range(freq)

    try:
        with _open_device() as dev:
            dev.write(f':LEV {gain}dBm')
            dev.write(f':FREQ {freq}')
            dev.write(":OUTP 1")
            dev.write(":MOD:STAT 1")
            dev.write(":PULM:SOUR EXT")
            dev.write(":PULM:STAT 1")
    except Exception as e:
        raise SignalConnectionError(f"Ошибка настройки Rabi: {e}") from e

def shutdown_rabi():
    try:
        with _open_device() as dev:
            dev.write(":OUTP 0")
            dev.write(":MOD:STAT 0")
            dev.write(":PULM:STAT 0")
    except Exception as e:
        raise SignalConnectionError(f"Ошибка отключения Rabi: {e}") from e

def set_freq(gain: int, freq: float):
    _check_gain_range(gain)
    _check_freq_range(freq)

    try:
        with _open_device() as dev:
            dev.write(f':LEV {gain}dBm')
            dev.write(f':FREQ {freq}')
            dev.write(":OUTP 1")
    except Exception as e:
        raise SignalConnectionError(f"Ошибка установки частоты: {e}") from e

def get_freq() -> float:
    try:
        with _open_device() as dev:
            return float(dev.query(":FREQ?").strip())
    except Exception as e:
        raise SignalConnectionError(f"Ошибка чтения частоты: {e}") from e

def setup_sweep(gain: int, start_freq: float, stop_freq: float, step_freq: float):
    _check_gain_range(gain)
    _check_freq_range(start_freq)
    _check_freq_range(stop_freq)

    if start_freq >= stop_freq:
        raise SignalParameterError("Начальная частота должна быть меньше конечной")
    if step_freq <= 0:
        raise SignalParameterError("Шаг частоты должен быть положительным")

    points = int(round((stop_freq - start_freq) / step_freq)) + 1
    if points > 65535:
        raise SignalParameterError(f"Слишком много точек: {points} (максимум 65535)")

    try:
        with _open_device() as dev:
            dev.write(':SWE:RES')
            dev.write(f':LEV {gain}dBm')
            dev.write(':SOUR1:FUNC:MODE SWE')
            dev.write(":SWE:MODE CONT")
            dev.write(":SWE:STEP:SHAP RAMP")
            dev.write(":SWE:TYPE STEP")
            dev.write(f":SWE:STEP:POIN {points}")
            dev.write(f":SWE:STEP:STAR:FREQ {start_freq}")
            dev.write(f":SWE:STEP:STOP:FREQ {stop_freq}")
            dev.write("SWE:POIN:TRIG:TYPE EXT")
            dev.write(":OUTP 1")
    except Exception as e:
        raise SignalConnectionError(f"Ошибка настройки свипа: {e}") from e

def shutdown_sweep():
    try:
        with _open_device() as dev:
            dev.write(":OUTP 0")
    except Exception as e:
        raise SignalConnectionError(f"Ошибка отключения свипа: {e}") from e