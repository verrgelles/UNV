import time
import serial
from serial.serialwin32 import Serial
from hardware.exceptions import SerialConnectionError, MirrorCommunicationError

# Константы
MIRRORS_COM_PORT = 'COM9'
VOLTAGE_TO_LENGTH_X = 32.13 / 1.340
LENGTH_TO_VOLTAGE_X = 1 / VOLTAGE_TO_LENGTH_X
VOLTAGE_TO_LENGTH_Y = 31.46 / 0.940
LENGTH_TO_VOLTAGE_Y = 1 / VOLTAGE_TO_LENGTH_Y

def open_serial_port() -> Serial:
    """Открывает порт управления зеркалами."""
    try:
        device = serial.Serial(MIRRORS_COM_PORT, 115200, timeout=0.01)
        if not device.isOpen():
            device.open()
        return device
    except serial.SerialException as e:
        raise SerialConnectionError("Не удалось открыть COM-порт зеркал") from e

def length_to_voltage(length: float, axis: str) -> float:
    if axis == 'x':
        factor = LENGTH_TO_VOLTAGE_X
    elif axis == 'y':
        factor = LENGTH_TO_VOLTAGE_Y
    else:
        raise ValueError(f"Неверная ось: {axis}")

    voltage = 1.650 - factor * length

    if 0.0 <= voltage <= 3.3:
        return voltage
    else:
        raise ValueError("Недопустимое значение напряжения")

def voltage_to_length(voltage: float, axis: str) -> float:
    if axis == 'x':
        factor = VOLTAGE_TO_LENGTH_X
    elif axis == 'y':
        factor = VOLTAGE_TO_LENGTH_Y
    else:
        raise ValueError(f"Неверная ось: {axis}")

    if 0.0 <= voltage <= 3.3:
        return factor * (1.650 - voltage)
    else:
        raise ValueError("Недопустимое значение напряжения")

def move_command(serial_device: Serial, x: float, y: float):
    """Отправляет команду на установку зеркал."""
    if 0 <= x <= 3.3 and 0 <= y <= 3.3:
        command = f"{x:.3f}|{y:.3f}F"
        serial_device.write(command.encode())
    else:
        raise MirrorCommunicationError("Напряжение вне допустимого диапазона в move_command")

# Позиция относительно центра (0,0) задаётся
def move_to_position(serial_device: Serial, position):
    x_target = length_to_voltage(position[0], axis='x')
    y_target = length_to_voltage(position[1], axis='y')

    if not (0 <= x_target <= 3.3 and 0 <= y_target <= 3.3):
        raise MirrorCommunicationError("Целевая позиция вне допустимого диапазона")

    move_command(serial_device, x_target, y_target)

def get_position(serial_device: Serial):
    """Читает текущую позицию зеркал в длинах."""
    try:
        serial_device.write(b"GETVOLTAGEFF")
        time.sleep(0.1)
        data = serial_device.readline()

        if len(data) <= 5:
            raise MirrorCommunicationError("Ответ от устройства слишком короткий")

        x_str, y_str = data.decode().strip().split('|')
        x, y = float(x_str), float(y_str)

        if not (0 <= x <= 3.3 and 0 <= y <= 3.3):
            raise MirrorCommunicationError("Неверные значения напряжения от зеркал")

        return [voltage_to_length(x, 'x'), voltage_to_length(y, 'y')]

    except Exception as e:
        raise MirrorCommunicationError("Не удалось получить позицию зеркал") from e
