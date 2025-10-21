import sys
import threading
import queue
import numpy as np
import pcapy

from matplotlib.figure import Figure
from pyvisa import ResourceManager
from scipy.special.cython_special import eval_sh_legendre
from hardware.mirrors import open_serial_port, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QThread, pyqtSignal

# --- Настройки ---
av_pulse = 15
count_time = 5
shift = 10

start_t = shift + np.arange(av_pulse) * 2 * count_time - 5
stop_t = start_t + count_time

start_t = np.append(start_t, 0)
stop_t = np.append(stop_t, max(stop_t) + 3)

start_t = np.append(start_t, stop_t[-1])
stop_t = np.append(stop_t, stop_t[-1] + 5)

start = 2860 * 1E6
stop = 2880 * 1E6
step = 50 * 1E3
gain = 0
RES = "USB0::0x1AB1::0x099C::DSG3G264300050::INSTR"

iface = "Ethernet"
cap = pcapy.open_live(iface, 106, 0, 0)  # snaplen=106, promisc=0, timeout=0
cap.setfilter("udp and src host 192.168.1.2")

frequencies = np.arange(start=start, stop=(stop + step), step=step)

rm = ResourceManager()
dev = rm.open_resource(RES)
dev.write(f':SWE:RES')
dev.write(f':LEV {gain}dBm')
dev.write(':SOUR1:FUNC:MODE SWE')
dev.write(":SWE:MODE CONT")
dev.write(":SWE:STEP:SHAP RAMP")
dev.write(":SWE:TYPE STEP")
dev.write(f":SWE:STEP:POIN {len(frequencies)}")
dev.write(f":SWE:STEP:STAR:FREQ {start}")
dev.write(f":SWE:STEP:STOP:FREQ {stop}")
dev.write("SWE:POIN:TRIG:TYPE EXT")
dev.write(":OUTP 1")

impulse_builder(
    3,
    [0, 3, 8],
    [av_pulse, 1, 1],
    start_t.tolist(),
    stop_t.tolist(),
    5000,
    int(1E6),
    int(1E3)
)

# --- Очередь для передачи данных ---
packet_queue = queue.Queue(maxsize=100000)

# --- Поток обработки пакетов ---
def packet_thread():
    def handle_packet(pwk, packet):
        global packet_queue
        rw = packet[42:]  # обрезаем заголовки
        k = raw_packet_to_dict(rw)
        if k.get('flag_neg') == 1:
            packet_queue.put_nowait(k['count_neg'] / av_pulse)

    cap.loop(-1, handle_packet)

threading.Thread(target=packet_thread, daemon=True).start()

# --- Сбор данных ---
def collect_data():
    ph_data = []
    while len(ph_data) < len(frequencies):
        if not packet_queue.empty():
            ph_data.append(packet_queue.get())
    return np.array(ph_data)

# --- Усреднение данных ---
def average_data(ph_data, num_averages):
    ph_avg = ph_data.copy()
    for _ in range(num_averages - 1):
        new_data = collect_data()
        ph_avg += new_data
    ph_avg /= num_averages
    return ph_avg


# --- Основной класс интерфейса ---
class MainWindow(QWidget):
    data_updated = pyqtSignal()  # Сигнал для обновления графика

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Photon Count vs Frequency")
        self.setGeometry(100, 100, 800, 600)

        # Создаем виджет для отображения графика
        self.canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.ax = self.canvas.figure.subplots()

        # Создаем кнопку для старта
        self.button = QPushButton("Start Averaging", self)
        self.button.clicked.connect(self.start_averaging)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.num_averages = 5
        self.ph_avg = None
        self.ph_data = None

        # Подключаем сигнал для обновления графика
        self.data_updated.connect(self.update_graph)

    def start_averaging(self):
        """Запуск усреднения и сбора данных"""
        # Начнем собирать и усреднять данные
        self.ph_data = collect_data()  # Первоначальный сбор данных
        self.ph_avg = average_data(self.ph_data, self.num_averages)

        # По завершении усреднения обновляем график
        self.data_updated.emit()

    def update_graph(self):
        """Обновление графика"""
        if self.ph_avg is not None:
            self.ax.clear()
            self.ax.plot(frequencies[2:], self.ph_avg[2:])
            self.ax.set_xlabel("Frequency (Hz)")
            self.ax.set_ylabel("Photon count")
            self.ax.set_title("Photon count vs Frequency (Averaged)")
            self.ax.grid(True)
            self.canvas.draw()

    def closeEvent(self, event):
        """Закрытие окна"""
        event.accept()


# Запуск приложения
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())