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
        return LENGTH_TO_VOLTAGE_X * length
    elif axis == 'y':
        return LENGTH_TO_VOLTAGE_Y * length
    raise ValueError(f"Неверная ось: {axis}")

def voltage_to_length(voltage: float, axis: str) -> float:
    if axis == 'x':
        return VOLTAGE_TO_LENGTH_X * voltage
    elif axis == 'y':
        return VOLTAGE_TO_LENGTH_Y * voltage
    raise ValueError(f"Неверная ось: {axis}")

def move_command(serial_device: Serial, x: float, y: float):
    """Отправляет команду на установку зеркал."""
    if 0 <= x <= 3.3 and 0 <= y <= 3.3:
        command = f"{x:.3f}|{y:.3f}F"
        serial_device.write(command.encode())
    else:
        raise MirrorCommunicationError("Напряжение вне допустимого диапазона в move_command")

def move_to_position(serial_device: Serial, center: [float, float], position: [float, float]):
    #FIXME тут может быть ошибка, проверить
    """Перемещает зеркала в точку относительно центра."""
    def get_voltage(pos, center_pos, axis):
        offset = length_to_voltage(abs(pos), axis)
        if pos >= center_pos:
            return 1.650 - offset
        else:
            return 1.650 + offset

    x_center_v = get_voltage(center[0], 0, 'x')
    y_center_v = get_voltage(center[1], 0, 'y')

    x_target_v = get_voltage(position[0], center[0], 'x')
    y_target_v = get_voltage(position[1], center[1], 'y')

    if not (0 <= x_target_v <= 3.3 and 0 <= y_target_v <= 3.3):
        raise MirrorCommunicationError("Целевая позиция вне допустимого диапазона")

    move_command(serial_device, x_target_v, y_target_v)

def get_position(serial_device: Serial) -> [float, float]:
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

        def _calc_length(voltage, axis):
            if 3.3 >= voltage >= 1.650:
                return 0 - length_to_voltage(voltage, axis)
            elif 0 <= voltage < 1.650:
                return 0 + length_to_voltage(voltage, axis)

        return [_calc_length(x, 'x'), _calc_length(y, 'y')]

    except Exception as e:
        raise MirrorCommunicationError("Не удалось получить позицию зеркал") from e
