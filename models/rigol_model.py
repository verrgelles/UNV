from PyQt6.QtCore import QObject, pyqtSignal
from hardware import rigol_rw as rigol
from hardware.exceptions import SignalConnectionError, SignalParameterError


class RigolModel(QObject):
    errorOccurred = pyqtSignal(str)
    frequencyChanged = pyqtSignal(float)
    outputStateChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.gain = 0
        self.freq = 1e6  # Hz
        self.output_on = False

    def setup_rabi(self):
        """Настройка генератора для эксперимента Раби."""
        try:
            rigol.setup_rabi(self.gain, self.freq)
            self.output_on = True
            self.outputStateChanged.emit(True)
        except (SignalParameterError, SignalConnectionError) as e:
            self._handle_error(str(e))

    def set_freq(self, freq: float):
        """Устанавливает частоту вручную."""
        self.freq = freq
        try:
            rigol.set_freq(self.gain, self.freq)
            self.frequencyChanged.emit(freq)
        except (SignalParameterError, SignalConnectionError) as e:
            self._handle_error(str(e))

    def get_freq(self) -> float | None:
        """Получает текущую частоту генератора."""
        try:
            freq = rigol.get_freq()
            self.freq = freq
            self.frequencyChanged.emit(freq)
            return freq
        except SignalConnectionError as e:
            self._handle_error(str(e))
            return None

    def sweep(self, start: float, stop: float, step: float):
        """Настройка частотной развёртки."""
        try:
            rigol.setup_sweep(self.gain, start, stop, step)
            self.output_on = True
            self.outputStateChanged.emit(True)
        except (SignalParameterError, SignalConnectionError) as e:
            self._handle_error(str(e))

    def shutdown(self):
        """Отключает выход генератора."""
        try:
            rigol.shutdown_rabi()
            self.output_on = False
            self.outputStateChanged.emit(False)
        except SignalConnectionError as e:
            self._handle_error(str(e))

    def shutdown_sweep(self):
        """Отключает генератор после свипа."""
        try:
            rigol.shutdown_sweep()
            self.output_on = False
            self.outputStateChanged.emit(False)
        except SignalConnectionError as e:
            self._handle_error(str(e))

    def _handle_error(self, message: str):
        self.errorOccurred.emit(message)