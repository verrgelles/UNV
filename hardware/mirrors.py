import time
import serial
from serial.serialwin32 import Serial
from hardware.exceptions import SerialConnectionError, MirrorCommunicationError

class MirrorsDriver:
    def __init__(self,COM_PORT = 'COM9'):
        self.MIRRORS_COM_PORT = COM_PORT
        self.VOLTAGE_TO_LENGTH_X = 32.13 / 1.340
        self.LENGTH_TO_VOLTAGE_X = 1 / self.VOLTAGE_TO_LENGTH_X
        self.VOLTAGE_TO_LENGTH_Y = 31.46 / 0.940
        self.LENGTH_TO_VOLTAGE_Y = 1 / self.VOLTAGE_TO_LENGTH_Y
        self.device = None
    def __del__(self):
        if self.device:
            self.device.close()
    def open_serial_port(self):
        """Открывает порт управления зеркалами."""
        try:
            self.device = serial.Serial(self.MIRRORS_COM_PORT, 115200, timeout=0.01)
            if not self.device.isOpen():
                self.device.open()
        except serial.SerialException as e:
            raise SerialConnectionError("Не удалось открыть COM-порт зеркал") from e

    def length_to_voltage(self,length: float, axis: str) -> float:
        if axis == 'x':
            factor = self.LENGTH_TO_VOLTAGE_X
        elif axis == 'y':
            factor = self.LENGTH_TO_VOLTAGE_Y
        else:
            raise ValueError(f"Неверная ось: {axis}")

        voltage = 1.650 - factor * length

        if 0.0 <= voltage <= 3.3:
            return voltage
        else:
            raise ValueError("Недопустимое значение напряжения")

    def voltage_to_length(self,voltage: float, axis: str) -> float:
        if axis == 'x':
            factor = self.VOLTAGE_TO_LENGTH_X
        elif axis == 'y':
            factor = self.VOLTAGE_TO_LENGTH_Y
        else:
            raise ValueError(f"Неверная ось: {axis}")

        if 0.0 <= voltage <= 3.3:
            return factor * (1.650 - voltage)
        else:
            raise ValueError("Недопустимое значение напряжения")

    def move_command(self, x: float, y: float):
        """Отправляет команду на установку зеркал."""
        if 0 <= x <= 3.3 and 0 <= y <= 3.3:
            command = f"{x:.3f}|{y:.3f}F"
            self.device.write(command.encode())
        else:
            raise MirrorCommunicationError("Напряжение вне допустимого диапазона в move_command")

    # Позиция относительно центра (0,0) задаётся
    def move_to_position(self, position):
        x_target = self.length_to_voltage(position[0], axis='x')
        y_target = self.length_to_voltage(position[1], axis='y')

        if not (0 <= x_target <= 3.3 and 0 <= y_target <= 3.3):
            raise MirrorCommunicationError("Целевая позиция вне допустимого диапазона")

        self.move_command(x_target, y_target)

    def get_position(self):
        """Читает текущую позицию зеркал в длинах."""
        try:
            self.device.write(b"GETVOLTAGEFF")
            time.sleep(0.1)
            data = self.device.readline()

            if len(data) <= 5:
                raise MirrorCommunicationError("Ответ от устройства слишком короткий")

            x_str, y_str = data.decode().strip().split('|')
            x, y = float(x_str), float(y_str)

            if not (0 <= x <= 3.3 and 0 <= y <= 3.3):
                raise MirrorCommunicationError("Неверные значения напряжения от зеркал")

            return [self.voltage_to_length(x, 'x'), self.voltage_to_length(y, 'y')]

        except Exception as e:
            raise MirrorCommunicationError("Не удалось получить позицию зеркал") from e
