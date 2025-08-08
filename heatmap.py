import sys
import threading
import time
import numpy as np
import pandas as pd
import pcapy

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFileDialog, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from hardware.mirrors import open_serial_port, move_to_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict


class WorkerSignals(QObject):
    finished = pyqtSignal()
    plot = pyqtSignal(pd.DataFrame)     # Отправляем сгруппированный DataFrame
    progress = pyqtSignal(int)
    log = pyqtSignal(str)


class HeatmapCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(7, 6))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.data = None
        self.cid = self.mpl_connect("button_press_event", self.on_click)
        self.device = None
        self.selected_point_marker = None
        self.annotation = None

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        self.divider = make_axes_locatable(self.ax)
        self.cax = self.divider.append_axes("right", size="5%", pad=0.1)
        self.colorbar = None

        # УДАЛИ: self._clim = None
        # self._clim больше не нужен — лимиты считаем каждый раз

    def plot(self, df: pd.DataFrame):
        self.ax.clear()
        self.cax.clear()
        self.selected_point_marker = None
        self.annotation = None

        # Регулярная сетка
        xs = np.sort(df['x'].unique())
        ys = np.sort(df['y'].unique())
        heatmap_data = df.pivot(index='y', columns='x', values='ph').reindex(index=ys, columns=xs)
        Z = heatmap_data.values

        # Лимиты для текущего кадра
        finite_vals = Z[np.isfinite(Z)]
        if finite_vals.size:
            vmin = float(np.nanmin(finite_vals))
            vmax = float(np.nanmax(finite_vals))
            # Если все значения одинаковые — слегка «раздвинем» диапазон, чтобы colorbar не падал
            if vmin == vmax:
                eps = 1e-9 if vmin == 0 else abs(vmin) * 1e-6
                vmin -= eps
                vmax += eps
        else:
            vmin, vmax = 0.0, 1.0

        X, Y = np.meshgrid(xs, ys)
        mesh = self.ax.pcolormesh(X, Y, Z, cmap='viridis', shading='auto', vmin=vmin, vmax=vmax)

        # Перестраиваем colorbar на каждый кадр
        self.colorbar = self.fig.colorbar(mesh, cax=self.cax)
        self.colorbar.set_label("Mean ph")

        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.ax.set_aspect('equal', adjustable='box')

        self.draw()
        self.data = df

    def on_click(self, event):
        if self.device is None or self.data is None:
            return
        if event.inaxes != self.ax:
            return

        x_click, y_click = event.xdata, event.ydata
        if x_click is None or y_click is None:
            return

        df = self.data.copy()
        df['dist'] = np.abs(df['x'] - x_click) + np.abs(df['y'] - y_click)
        nearest = df.loc[df['dist'].idxmin()]

        x_target, y_target = nearest['x'], nearest['y']

        # Переместить устройство
        drt = open_serial_port()
        move_to_position(drt, [x_target, y_target])

        # Удалить старый маркер
        if self.selected_point_marker:
            self.selected_point_marker.remove()
            self.selected_point_marker = None
        if self.annotation:
            self.annotation.remove()
            self.annotation = None

        # Добавить новый маркер и подпись
        self.selected_point_marker = self.ax.plot(
            x_target, y_target, marker='o', color='red', markersize=8
        )[0]
        self.annotation = self.ax.annotate(
            f"({x_target}, {y_target})",
            xy=(x_target, y_target),
            xytext=(5, 5),
            textcoords="offset points",
            color="white",
            backgroundcolor="black",
            fontsize=8
        )
        self.draw()


class ScannerThread(threading.Thread):
    def __init__(self, X, Y, step, time_to_collect, device, signals):
        super().__init__()
        self.X = X
        self.Y = Y
        self.step = step
        self.time_to_collect = time_to_collect
        self.device = device
        self.signals = signals
        self.dt = pd.DataFrame(columns=["x", "y", "ph"])

    def run(self):
        try:
            self.signals.log.emit("Инициализация оборудования...")
            impulse_builder(
                2, [0, 2], [1, 1], [0, 0],
                [self.time_to_collect]*2,
                150, int(1e6), int(1e3)
            )

            move_to_position(self.device, [0, 0])
            self.signals.log.emit("Начало сканирования...")

            xi = np.arange(-self.X/2, self.X/2 + self.step, self.step)
            yi = np.arange(self.Y/2, -(self.Y/2 + self.step), -self.step)

            total_points = len(xi) * len(yi)
            count = 0

            cap = pcapy.open_live("Ethernet", 106, 0, 0)
            cap.setfilter("udp and src host 192.168.1.2")
            max_count = int(8000 * self.time_to_collect * 1e-3)

            def handle_packet(_, pkt):
                nonlocal x_t, y_t, packet_count
                packet_count += 1
                if packet_count >= max_count:
                    raise KeyboardInterrupt()
                k = raw_packet_to_dict(pkt[42:])
                if k['flag_pos'] == 1:
                    self.dt.loc[len(self.dt)] = [round(x_t, 2), round(y_t, 2), k['count_pos']]

            def flush(cap, ft=0.1):
                t0 = time.time()
                while time.time() - t0 < ft:
                    try:
                        cap.dispatch(10, lambda *_: None)
                    except Exception:
                        break

            # === Сканирование построчно ===
            for y_t in yi:
                # можно сообщить о начале строки
                self.signals.log.emit(f"Строка y={y_t:.3f}...")
                for x_t in xi:
                    move_to_position(self.device, [x_t, y_t])
                    time.sleep(0.03)
                    flush(cap)
                    packet_count = 0
                    try:
                        cap.loop(-1, handle_packet)  # собираем точку
                    except KeyboardInterrupt:
                        pass

                    count += 1
                    self.signals.progress.emit(int(count / total_points * 100))

                # ==== НОВОЕ: обновление карты ПОСЛЕ ЗАВЕРШЕНИЯ СТРОКИ ====
                if not self.dt.empty:
                    df_row = (
                        self.dt.groupby(['x', 'y'], as_index=False)['ph']
                        .mean()
                        .sort_values(['y', 'x'])
                    )
                    self.signals.plot.emit(df_row)
                    self.signals.log.emit(f"Строка y={y_t:.3f} готова, точек: {len(df_row[df_row['y']==y_t])}")

            # финальный кадр
            self.dt = self.dt.groupby(['x', 'y'], as_index=False)['ph'].mean()
            self.signals.plot.emit(self.dt)
            self.signals.log.emit("Сканирование завершено.")

        except Exception as e:
            self.signals.log.emit(f"Ошибка: {e}")
        finally:
            try:
                self.device.close()
                self.signals.log.emit("COM-порт зеркал закрыт.")
            except Exception as e:
                self.signals.log.emit(f"Ошибка при закрытии порта: {e}")

        self.signals.finished.emit()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Сканер тепловой карты")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.heatmap_canvas = HeatmapCanvas(self)
        layout.addWidget(NavigationToolbar(self.heatmap_canvas, self))
        layout.addWidget(self.heatmap_canvas)

        self.inputs = {}
        for label in ["X", "Y", "Шаг", "Время сбора (мс)"]:
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(label))
            le = QLineEdit()
            hbox.addWidget(le)
            layout.addLayout(hbox)
            self.inputs[label] = le

        self.estimate = QLabel("Ожидаемое время: —")
        layout.addWidget(self.estimate)

        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Сканировать")
        self.start_btn.clicked.connect(self.start_scan)
        button_layout.addWidget(self.start_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_heatmap)
        button_layout.addWidget(self.save_btn)

        self.load_btn = QPushButton("Загрузить")
        self.load_btn.clicked.connect(self.load_heatmap)
        button_layout.addWidget(self.load_btn)

        layout.addLayout(button_layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        self.setLayout(layout)

    def start_scan(self):
        try:
            X = float(self.inputs["X"].text())
            Y = float(self.inputs["Y"].text())
            step = float(self.inputs["Шаг"].text())
            t = round(int(self.inputs["Время сбора (мс)"].text()) / 2)
            if t <= 0:
                raise ValueError("Время должно быть больше нуля")

            self.device = open_serial_port()
            self.heatmap_canvas.device = self.device
            self.log_output.append("COM-порт зеркал открыт")

            xi = np.arange(-X / 2, X / 2 + step, step)
            yi = np.arange(Y / 2, -(Y / 2 + step), -step)
            total = len(xi) * len(yi)
            estimated = total * (0.03 + t / 1000)
            self.estimate.setText(f"Ожидаемое время: ~{estimated:.1f} сек")

            self.start_btn.setEnabled(False)
            self.progress.setValue(0)

            self.signals = WorkerSignals()
            self.signals.progress.connect(self.progress.setValue)
            self.signals.log.connect(self.log_output.append)
            self.signals.plot.connect(self.display_plot)
            self.signals.finished.connect(self.on_finished)

            self.worker = ScannerThread(X, Y, step, t, self.device, self.signals)
            self.worker.start()

            self.log_output.append("Сканирование запущено (обновление — построчно).")

        except Exception as e:
            self.log_output.append(f"Ошибка запуска: {e}")

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.estimate.setText("Ожидаемое время: —")

    def display_plot(self, df):
        self.heatmap_canvas.plot(df)

    def save_heatmap(self):
        if self.heatmap_canvas.data is not None:
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", "", "CSV Files (*.csv)")
            if path:
                self.heatmap_canvas.data.to_csv(path, index=False)
                self.log_output.append(f"Сохранено: {path}")

    def load_heatmap(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить CSV", "", "CSV Files (*.csv)")
        if path:
            df = pd.read_csv(path)
            self.heatmap_canvas.plot(df)
            self.log_output.append(f"Загружено: {path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 800)
    window.show()
    sys.exit(app.exec())
