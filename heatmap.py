import sys
import threading
import time
import numpy as np
import pandas as pd
import seaborn as sns
import pcapy

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from hardware.mirrors import open_serial_port, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict


class WorkerSignals(QObject):
    finished = pyqtSignal()
    log = pyqtSignal(str)
    plot = pyqtSignal(pd.DataFrame, object)


class HeatmapCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(7, 6))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.data = None
        self.cid = self.mpl_connect("button_press_event", self.on_click)
        self.device = None

    def plot(self, df):
        self.ax.clear()
        heatmap_data = df.pivot(index='y', columns='x', values='ph')
        sns.heatmap(heatmap_data, cmap="viridis", ax=self.ax, cbar_kws={'label': 'Mean ph'})
        self.ax.invert_yaxis()
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.draw()
        self.data = df

    def on_click(self, event):
        if self.device is None or self.data is None:
            return
        if event.inaxes != self.ax:
            return

        x_click = event.xdata
        y_click = event.ydata

        df = self.data.copy()
        df['dist'] = np.sqrt((df['x'] - x_click)**2 + (df['y'] - y_click)**2)
        nearest = df.loc[df['dist'].idxmin()]

        x_target, y_target = nearest['x'], nearest['y']
        move_to_position(self.device, [x_target, y_target])
        print(f"Moved to: ({x_target}, {y_target})")


class ScannerThread(threading.Thread):
    def __init__(self, X, Y, step, time_to_collect, signals):
        super().__init__()
        self.X = X
        self.Y = Y
        self.step = step
        self.time_to_collect = time_to_collect
        self.signals = signals
        self.dt = pd.DataFrame(columns=["x", "y", "ph"])

    def run(self):
        try:
            impulse_builder(
                2,
                [0, 2],
                [1, 1],
                [0, 0],
                [self.time_to_collect, self.time_to_collect],
                150,
                int(1E6),
                int(1E3)
            )

            dev = open_serial_port()
            center = [0,0]
            move_to_position(dev, center)

            xi = np.arange(-self.X / 2 + center[0], self.X / 2 + center[0] + self.step, self.step)
            yi = np.arange(self.Y / 2 + center[1], -(self.Y / 2 - center[1] + self.step), -self.step)

            iface = "Ethernet"
            cap = pcapy.open_live(iface, 106, 0, 0)
            cap.setfilter("udp and src host 192.168.1.2")
            packet_speed = 8000
            max_count = int(packet_speed * self.time_to_collect * 1E-3)

            def handle_packet(_hdr, packet):
                nonlocal x_t, y_t, packet_count
                packet_count += 1
                if packet_count >= max_count:
                    raise KeyboardInterrupt()
                rw = packet[42:]
                k = raw_packet_to_dict(rw)
                if k['flag_pos'] == 1:
                    self.dt.loc[len(self.dt)] = {"x": round(x_t, 2), "y": round(y_t, 2), "ph": k['count_pos']}

            def flush_buffer(capture, flush_time=0.1):
                start = time.time()
                def _flush(_hdr, _data):
                    pass
                while True:
                    try:
                        capture.dispatch(10, _flush)
                    except:
                        break
                    if time.time() - start > flush_time:
                        break

            q = time.perf_counter_ns()
            for y_t in yi:
                for x_t in xi:
                    move_to_position(dev, [x_t, y_t])
                    time.sleep(0.03)
                    flush_buffer(cap, 0.03)
                    packet_count = 0
                    try:
                        cap.loop(-1, handle_packet)
                    except KeyboardInterrupt:
                        continue

            self.dt = self.dt.groupby(['x', 'y'], as_index=False)['ph'].mean()
            self.dt.to_csv("scan_output.csv")

            elapsed = (time.perf_counter_ns() - q) * 1E-9
            self.signals.log.emit(f"Сканирование завершено за {elapsed:.2f} сек")
            self.signals.plot.emit(self.dt, dev)

        except Exception as e:
            self.signals.log.emit(f"Ошибка: {str(e)}")
        self.signals.finished.emit()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Сканер тепловой карты")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.inputs = {}
        for label in ["X", "Y", "Шаг", "Время сбора (мс)"]:
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(label))
            line_edit = QLineEdit()
            hbox.addWidget(line_edit)
            layout.addLayout(hbox)
            self.inputs[label] = line_edit

        self.start_btn = QPushButton("Запустить сканирование")
        self.start_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.start_btn)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.heatmap_canvas = HeatmapCanvas(self)
        layout.addWidget(self.heatmap_canvas)

        self.setLayout(layout)

    def log(self, message):
        self.log_box.append(message)

    def start_scan(self):
        try:
            X = int(self.inputs["X"].text())
            Y = int(self.inputs["Y"].text())
            step = float(self.inputs["Шаг"].text())
            time_to_collect = round(int(self.inputs["Время сбора (мс)"].text()) / 2)

            if time_to_collect <= 0:
                raise ValueError("Время должно быть больше нуля")

            self.log(f"Параметры: X={X}, Y={Y}, шаг={step}, время={time_to_collect}мс")
            self.start_btn.setEnabled(False)

            self.signals = WorkerSignals()
            self.signals.log.connect(self.log)
            self.signals.finished.connect(self.on_scan_finished)
            self.signals.plot.connect(self.display_plot)

            self.worker = ScannerThread(X, Y, step, time_to_collect, self.signals)
            self.worker.start()

        except Exception as e:
            self.log(f"Ошибка ввода: {str(e)}")

    def display_plot(self, df, dev):
        self.heatmap_canvas.device = dev
        self.heatmap_canvas.plot(df)

    def on_scan_finished(self):
        self.log("Сканирование завершено.")
        self.start_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 800)
    window.show()
    sys.exit(app.exec())