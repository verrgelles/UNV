from PyQt6.QtCore import QObject, pyqtSignal
from hardware import spincore
from hardware.exceptions import SpinCoreExecutionError


class SpinCoreModel(QObject):
    errorOccurred = pyqtSignal(str)
    stateChanged = pyqtSignal(bool)  # True = running, False = stopped

    def __init__(self):
        super().__init__()
        self.running = False

    def load_impulse_program(self, config: dict):
        """
        Загружает программу импульсов в спинкор.
        config — это словарь с параметрами:
        {
            'num_channels': int,
            'channel_numbers': list[int],
            'impulse_counts': list[int],
            'start_times': list[int],
            'stop_times': list[int],
            'repeat_time': int,
            'pulse_scale': int,
            'rep_scale': int
        }
        """
        try:
            spincore.impulse_builder(**config)
        except Exception as e:
            self._handle_error(f"Ошибка при загрузке импульсной программы: {e}")

    def start(self):
        """Запускает выполнение программы."""
        try:
            spincore.start()
            self.running = True
            self.stateChanged.emit(True)
        except Exception as e:
            self._handle_error(f"Ошибка запуска: {e}")

    def stop(self):
        """Останавливает выполнение программы."""
        try:
            spincore.stop()
            self.running = False
            self.stateChanged.emit(False)
        except Exception as e:
            self._handle_error(f"Ошибка остановки: {e}")

    def close(self):
        """Закрывает соединение со SpinCore."""
        try:
            spincore.close()
            self.running = False
            self.stateChanged.emit(False)
        except Exception as e:
            self._handle_error(f"Ошибка закрытия: {e}")

    def _handle_error(self, message: str):
        """Вызывает сигнал ошибки и обновляет статус."""
        self.errorOccurred.emit(message)
        self.running = False
        self.stateChanged.emit(False)
