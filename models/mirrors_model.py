from PyQt6.QtCore import QObject, pyqtSignal
from hardware.mirrors import MirrorsDriver
from hardware.exceptions import SerialConnectionError


class MirrorsModel(QObject):
    errorOccurred = pyqtSignal(str)
    positionChanged = pyqtSignal(list)  # [x, y] в длинах

    def __init__(self):
        super().__init__()
        self.mirrors = MirrorsDriver()
        self.center = [0.0, 0.0]  # Центр координат

    def connect(self):
        """Открывает порт управления зеркалами."""
        try:
            self.mirrors.open_serial_port()
        except SerialConnectionError as e:
            self._handle_error(str(e))

    def move_to(self, position: [float, float]):
        """
        Перемещает зеркала в заданную позицию (в длинах, мкм).
        """
        if not self.mirrors:
            self._handle_error("Зеркала не подключены")
            return

        try:
            #self.mirrors.move_to_position(self.center, position)
            self.mirrors.move_to_position(position)
            self.positionChanged.emit(position)
        except Exception as e:
            self._handle_error(f"Ошибка перемещения: {e}")

    def get_position(self):
        """
        Получает текущую позицию зеркал.
        """
        if not self.mirrors:
            self._handle_error("Зеркала не подключены")
            return None

        try:
            pos = self.mirrors.get_position()
            if pos:
                self.positionChanged.emit(pos)
                return pos
            else:
                self._handle_error("Не удалось получить позицию зеркал")
        except Exception as e:
            self._handle_error(f"Ошибка получения позиции: {e}")
        return None

    def _handle_error(self, message: str):
        """Обрабатывает ошибку и эмитит сигнал для UI."""
        self.errorOccurred.emit(message)
