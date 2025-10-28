import time
import serial
from serial.serialwin32 import Serial
from hardware.exceptions import SerialConnectionError, MirrorCommunicationError

# CONSTANTS
MIRRORS_COM_PORT = 'COM9'
VOLTAGE_TO_LENGTH_X = 32.13 / 1.340
VOLTAGE_TO_LENGTH_Y = 31.46 / 0.940


def open_serial_port() -> Serial:
    """Открывает порт управления зеркалами."""
    try:
        device = serial.Serial(MIRRORS_COM_PORT, 115200, timeout=0.01)
        if not device.isOpen():
            device.open()
        return device
    except serial.SerialException as e:
        raise SerialConnectionError("Не удалось открыть COM-порт зеркал") from e

def move_command(serial_device: Serial, x: float, y: float):
    """Отправляет команду на установку зеркал."""
    if 0 <= x <= 3.3 and 0 <= y <= 3.3:
        command = f"{x:.3f}|{y:.3f}F"
        serial_device.write(command.encode())
    else:
        raise MirrorCommunicationError("Напряжение вне допустимого диапазона в move_command")

ser = open_serial_port()
x=1.65
y=1.65
x_0 = 1.65
y_0 = 1.65
move_command(ser, x,y)
step = -0.05
while True:
    f = str(input())
    if not f:
        continue
    match f[0]:
        case 'w':
            y+=step
        case 's':
            y-=step
        case 'd':
            x+=step
        case 'a':
            x-=step
        case 'q':
            break
        case 'e':
            step = -float(input())
        case 'z':
            x_0 = x
            y_0 = y
    move_command(ser, x,y)
print(x,y)
print(x_0,y_0)
print(x-x_0,y-y_0)