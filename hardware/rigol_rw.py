from pyvisa import ResourceManager
from hardware.exceptions import SignalParameterError, SignalConnectionError

class RigolDriver:
    def __init__(self):
        self.RES_ = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"
        self.rm_ = ResourceManager()
        try:
            self.dev = self.rm_.open_resource(self.RES_)
        except Exception as e:
            raise SignalConnectionError(f"Не удалось открыть подключение к генератору: {e}") from e

    def _open_device(self):
        try:
            rm = ResourceManager()
            return rm.open_resource(self.RES_)
        except Exception as e:
            raise SignalConnectionError(f"Не удалось открыть подключение к генератору: {e}") from e

    def _check_freq_range(self,freq: float):
        if not (9e3 <= freq <= 13.6e9):
            raise SignalParameterError("Частота должна быть в диапазоне 9 kHz – 13.6 GHz")

    def _check_gain_range(self,gain: int):
        if not (-130 <= gain <= 27):
            raise SignalParameterError("Усиление должно быть в диапазоне [-130, 27] дБм")

    def setup_rabi(self,gain: int, freq: float):
        self._check_gain_range(gain)
        self._check_freq_range(freq)

        try:
            #with _open_device() as dev:
            self.dev.write(f':LEV {gain}dBm')
            self.dev.write(f':FREQ {freq}')
            self.dev.write(":OUTP 1")
            self.dev.write(":MOD:STAT 1")
            self.dev.write(":PULM:SOUR EXT")
            self.dev.write(":PULM:STAT 1")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка настройки Rabi: {e}") from e

    def shutdown_rabi(self):
        try:
            self.dev.write(":OUTP 0")
            self.dev.write(":MOD:STAT 0")
            self.dev.write(":PULM:STAT 0")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка отключения Rabi: {e}") from e

    def set_freq(self, gain: int, freq: float):
        self._check_gain_range(gain)
        self._check_freq_range(freq)

        try:
            self.dev.write(f':LEV {gain}dBm')
            self.dev.write(f':FREQ {freq}')
            self.dev.write(":OUTP 1")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка установки частоты: {e}") from e

    def get_freq(self) -> float:
        try:
            return float(self.dev.query(":FREQ?").strip())
        except Exception as e:
            raise SignalConnectionError(f"Ошибка чтения частоты: {e}") from e

    def setup_sweep(self,gain: int, start_freq: float, stop_freq: float, step_freq: float):
        self._check_gain_range(gain)
        self._check_freq_range(start_freq)
        self._check_freq_range(stop_freq)

        if start_freq >= stop_freq:
            raise SignalParameterError("Начальная частота должна быть меньше конечной")
        if step_freq <= 0:
            raise SignalParameterError("Шаг частоты должен быть положительным")

        points = int(round((stop_freq - start_freq) / step_freq)) + 1
        if points > 65535:
            raise SignalParameterError(f"Слишком много точек: {points} (максимум 65535)")

        try:
            self.dev.write(':SWE:RES')
            self.dev.write(f':LEV {gain}dBm')
            self.dev.write(':SOUR1:FUNC:MODE SWE')
            self.dev.write(":SWE:MODE CONT")
            self.dev.write(":SWE:STEP:SHAP RAMP")
            self.dev.write(":SWE:TYPE STEP")
            self.dev.write(f":SWE:STEP:POIN {points}")
            self.dev.write(f":SWE:STEP:STAR:FREQ {start_freq}")
            self.dev.write(f":SWE:STEP:STOP:FREQ {stop_freq}")
            self.dev.write("SWE:POIN:TRIG:TYPE EXT")
            self.dev.write(":OUTP 1")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка настройки свипа: {e}") from e

    def shutdown_sweep(self):
        try:
            self.dev.write(":OUTP 0")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка отключения свипа: {e}") from e
    def setup_sweep_for_imp_odmr(self,gain: int, start_freq: float, stop_freq: float, step_freq: float):
        self._check_gain_range(gain)
        self._check_freq_range(start_freq)
        self._check_freq_range(stop_freq)

        if start_freq >= stop_freq:
            raise SignalParameterError("Начальная частота должна быть меньше конечной")
        if step_freq <= 0:
            raise SignalParameterError("Шаг частоты должен быть положительным")

        points = int(round((stop_freq - start_freq) / step_freq)) + 1
        if points > 65535:
            raise SignalParameterError(f"Слишком много точек: {points} (максимум 65535)")

        try:
            self.dev.write(f':SWE:RES')
            self.dev.write(f':LEV {gain}dBm')
            self.dev.write(':SOUR1:FUNC:MODE SWE')
            self.dev.write(":SWE:MODE CONT")
            self.dev.write(":SWE:STEP:SHAP RAMP")
            self.dev.write(":SWE:TYPE STEP")
            self.dev.write(f":SWE:STEP:POIN {points}")
            self.dev.write(f":SWE:STEP:STAR:FREQ {start_freq}")
            self.dev.write(f":SWE:STEP:STOP:FREQ {stop_freq}")
            self.dev.write("SWE:POIN:TRIG:TYPE EXT")
            self.dev.write(":MOD:STAT 1")
            self.dev.write(":PULM:SOUR EXT")
            self.dev.write(":PULM:STAT 1")
            self.dev.write(":OUTP 1")
        except Exception as e:
            raise SignalConnectionError(f"Ошибка настройки свипа: {e}") from e