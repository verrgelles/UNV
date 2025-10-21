import sys
import threading
import time
import numpy as np
import pandas as pd
import pcapy

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFileDialog, QProgressBar, QTextEdit,
    QGridLayout, QMessageBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from hardware.mirrors import open_serial_port, move_to_position, get_position
from hardware.spincore import impulse_builder
from packets import raw_packet_to_dict


class WorkerSignals(QObject):
    finished = pyqtSignal()
    plot = pyqtSignal(pd.DataFrame)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    eta = pyqtSignal(str)


class HeatmapCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(7, 6))
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.data = None
        self.vmin_base = None
        self.vmax_base = None
        self.contrast_scale = 1.0
        self.cid = self.mpl_connect("button_press_event", self.on_click)
        self.device = None
        self.selected_point_marker = None
        self.annotation = None

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        self.divider = make_axes_locatable(self.ax)
        self.cax = self.divider.append_axes("right", size="5%", pad=0.1)
        self.colorbar = None

    def plot(self, df: pd.DataFrame):
        self.ax.clear()
        self.cax.clear()
        self.selected_point_marker = None
        self.annotation = None

        xs = np.sort(df['x'].unique())
        ys = np.sort(df['y'].unique())
        heatmap_data = df.pivot(index='y', columns='x', values='ph').reindex(index=ys, columns=xs)
        Z = heatmap_data.values

        finite_vals = Z[np.isfinite(Z)]
        if finite_vals.size:
            self.vmin_base = float(np.nanmin(finite_vals))
            self.vmax_base = float(np.nanmax(finite_vals))
            if self.vmin_base == self.vmax_base:
                eps = 1e-9 if self.vmin_base == 0 else abs(self.vmin_base) * 1e-6
                self.vmin_base -= eps
                self.vmax_base += eps
        else:
            self.vmin_base, self.vmax_base = 0.0, 1.0

        self._draw_heatmap(xs, ys, Z)
        self.data = df

    def _draw_heatmap(self, xs, ys, Z):
        vmin = self.vmin_base / self.contrast_scale
        vmax = self.vmax_base * self.contrast_scale

        self.ax.clear()
        self.cax.clear()
        mesh = self.ax.pcolormesh(xs, ys, Z, cmap='viridis', shading='auto', vmin=vmin, vmax=vmax)
        self.colorbar = self.fig.colorbar(mesh, cax=self.cax)
        self.colorbar.set_label("Mean ph")
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.ax.set_aspect('equal', adjustable='box')
        self.draw()

    def update_contrast(self, scale_percent: int):
        if self.data is None:
            return
        self.contrast_scale = scale_percent / 100.0
        xs = np.sort(self.data['x'].unique())
        ys = np.sort(self.data['y'].unique())
        Z = self.data.pivot(index='y', columns='x', values='ph').reindex(index=ys, columns=xs).values
        self._draw_heatmap(xs, ys, Z)

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
        drt = open_serial_port()
        move_to_position(drt, [x_target, y_target])
        if self.selected_point_marker:
            self.selected_point_marker.remove()
        if self.annotation:
            self.annotation.remove()
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
    def __init__(self, X, Y, step, time_to_collect_ms_div2, device, signals,
                 settle_s=0.03, flush_s=0.10, stop_event: threading.Event | None = None):
        super().__init__()
        self.X = X
        self.Y = Y
        self.step = step
        self.time_to_collect = int(time_to_collect_ms_div2)
        self.device = device
        self.signals = signals
        self.settle_s = float(settle_s)
        self.flush_s = float(flush_s)
        self.dt = pd.DataFrame(columns=["x", "y", "ph"])
        self.stop_event = stop_event or threading.Event()
        self._stopped_by_user = False

    def _should_stop(self) -> bool:
        if self.stop_event.is_set():
            self._stopped_by_user = True
            return True
        return False

    def _sleep_interruptible(self, seconds: float):
        t_end = time.time() + seconds
        while time.time() < t_end:
            if self._should_stop():
                break
            time.sleep(0.01)

    def run(self):
        try:
            self.signals.log.emit("Инициализация оборудования...")
            impulse_builder(
                2, [0, 3], [1, 1], [0, 0],
                [self.time_to_collect] * 2,
                150, int(1e6), int(1e3)
            )
            center = get_position(self.device)
            self.signals.log.emit("Начало сканирования...")

            xi = np.arange(-self.X/2 + center[0], self.X/2 + center[0] + self.step, self.step)
            yi = np.arange(self.Y/2 + center[1], -(self.Y/2 - center[1] + self.step), -self.step)
            total_points = len(xi) * len(yi)
            count = 0

            cap = pcapy.open_live("Ethernet", 106, 0, 0)
            cap.setfilter("udp and src host 192.168.1.2")
            max_count = int(8000 * self.time_to_collect * 1e-3)

            def handle_packet(_, pkt):
                if self._should_stop():
                    raise KeyboardInterrupt()
                nonlocal x_t, y_t, packet_count
                packet_count += 1
                if packet_count >= max_count:
                    raise KeyboardInterrupt()
                k = raw_packet_to_dict(pkt[42:])
                if k['flag_pos'] == 1:
                    self.dt.loc[len(self.dt)] = [round(x_t, 2), round(y_t, 2), k['count_pos']]

            def flush(cap, ft=None):
                ft = self.flush_s if ft is None else ft
                t0 = time.time()
                while time.time() - t0 < ft:
                    if self._should_stop():
                        break
                    cap.dispatch(10, lambda *_: None)

            t_start = time.time()
            for y_t in yi:
                if self._should_stop():
                    break
                self.signals.log.emit(f"Строка y={y_t:.3f}...")
                for x_t in xi:
                    if self._should_stop():
                        break
                    move_to_position(self.device, [x_t, y_t])
                    self._sleep_interruptible(self.settle_s)
                    flush(cap)
                    if self._should_stop():
                        break
                    packet_count = 0
                    try:
                        cap.loop(-1, handle_packet)
                    except KeyboardInterrupt:
                        pass
                    count += 1
                    self.signals.progress.emit(int(count / total_points * 100))
                    elapsed = time.time() - t_start
                    remaining = max(0, total_points - count)
                    per_point_collect = self.time_to_collect / 1000.0
                    avg_per_point_obs = elapsed / max(1, count)
                    per_point_est = max(avg_per_point_obs, per_point_collect + self.settle_s + self.flush_s)
                    eta_s = remaining * per_point_est
                    self.signals.eta.emit(self._fmt_eta(eta_s))
                if not self.dt.empty:
                    df_row = (
                        self.dt.groupby(['x', 'y'], as_index=False)['ph']
                        .mean()
                        .sort_values(['y', 'x'])
                    )
                    self.signals.plot.emit(df_row)
            if not self.dt.empty:
                self.dt = self.dt.groupby(['x', 'y'], as_index=False)['ph'].mean()
                self.signals.plot.emit(self.dt)
            self.signals.log.emit("Сканирование завершено." if not self._stopped_by_user else "Сканирование остановлено пользователем.")
        finally:
            try:
                self.device.close()
                self.signals.log.emit("COM-порт зеркал закрыт.")
            except Exception as e:
                self.signals.log.emit(f"Ошибка при закрытии порта: {e}")
            self.signals.finished.emit()

    @staticmethod
    def _fmt_eta(seconds: float) -> str:
        seconds = max(0, int(round(seconds)))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"Осталось ~{h}ч {m:02d}м {s:02d}с"
        if m:
            return f"Осталось ~{m}м {s:02d}с"
        return f"Осталось ~{s}с"


class MirrorControlWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление зеркалами")
        self.device = None
        self._init_ui()
        try:
            self.device = open_serial_port()
            self.status_label.setText("COM-порт: открыт")
        except Exception as e:
            self.status_label.setText(f"COM-порт: ошибка — {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть COM-порт: {e}")
        try:
            pos = get_position(self.device)
            self.x, self.y = float(pos[0]), float(pos[1])
        except Exception:
            self.x, self.y = 0.0, 0.0
        self._update_coord_label()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("COM-порт: —")
        self.coord_label = QLabel("Позиция: (0.00, 0.00)")
        layout.addWidget(self.status_label)
        layout.addWidget(self.coord_label)
        step_box = QHBoxLayout()
        step_box.addWidget(QLabel("Шаг:"))
        self.step_edit = QLineEdit("0.10")
        self.step_edit.setMaximumWidth(100)
        step_box.addWidget(self.step_edit)
        layout.addLayout(step_box)
        grid = QGridLayout()
        btn_up = QPushButton("↑"); btn_down = QPushButton("↓")
        btn_left = QPushButton("←"); btn_right = QPushButton("→")
        btn_center = QPushButton("В центр"); btn_close = QPushButton("Завершить")
        btn_up.clicked.connect(self.move_up)
        btn_down.clicked.connect(self.move_down)
        btn_left.clicked.connect(self.move_left)
        btn_right.clicked.connect(self.move_right)
        btn_center.clicked.connect(self.move_center)
        btn_close.clicked.connect(self.finish)
        grid.addWidget(btn_up,0,1); grid.addWidget(btn_left,1,0)
        grid.addWidget(btn_center,1,1); grid.addWidget(btn_right,1,2)
        grid.addWidget(btn_down,2,1)
        layout.addLayout(grid)
        layout.addSpacing(8)
        layout.addWidget(btn_close)
        self.setLayout(layout)
        self.resize(300, 220)

    def _get_step(self) -> float:
        try:
            s = float(self.step_edit.text())
            if s <= 0:
                raise ValueError
            return s
        except Exception:
            QMessageBox.warning(self, "Шаг", "Некорректный шаг. Использую 0.10")
            self.step_edit.setText("0.10")
            return 0.10

    def _apply_move(self):
        if self.device is None:
            QMessageBox.warning(self, "Порт закрыт", "COM-порт не открыт.")
            return
        move_to_position(self.device, [self.x, self.y])
        self._update_coord_label()

    def _update_coord_label(self):
        self.coord_label.setText(f"Позиция: ({self.x:.2f}, {self.y:.2f})")

    def move_up(self): self.y += self._get_step(); self._apply_move()
    def move_down(self): self.y -= self._get_step(); self._apply_move()
    def move_left(self): self.x -= self._get_step(); self._apply_move()
    def move_right(self): self.x += self._get_step(); self._apply_move()
    def move_center(self): self.x, self.y = 0.0, 0.0; self._apply_move()
    def finish(self): self.close()
    def closeEvent(self, event):
        try:
            if self.device:
                self.device.close()
        except Exception:
            pass
        event.accept()


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
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Контраст"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(10, 200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(lambda v: self.heatmap_canvas.update_contrast(v))
        contrast_layout.addWidget(self.contrast_slider)
        layout.addLayout(contrast_layout)
        self.inputs = {}
        for label in ["X", "Y", "Шаг", "Время сбора (мс)"]:
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(label))
            le = QLineEdit()
            hbox.addWidget(le)
            layout.addLayout(hbox)
            self.inputs[label] = le
        self.eta_label = QLabel("Осталось: —")
        layout.addWidget(self.eta_label)
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Сканировать"); self.start_btn.clicked.connect(self.start_scan)
        self.stop_btn = QPushButton("Остановить"); self.stop_btn.setEnabled(False); self.stop_btn.clicked.connect(self.stop_scan)
        self.save_btn = QPushButton("Сохранить"); self.save_btn.clicked.connect(self.save_heatmap)
        self.load_btn = QPushButton("Загрузить"); self.load_btn.clicked.connect(self.load_heatmap)
        self.mirror_ctrl_btn = QPushButton("Управление зеркалами"); self.mirror_ctrl_btn.clicked.connect(self.open_mirror_control)
        for b in [self.start_btn, self.stop_btn, self.save_btn, self.load_btn, self.mirror_ctrl_btn]:
            button_layout.addWidget(b)
        layout.addLayout(button_layout)
        self.log_output = QTextEdit(); self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.setLayout(layout)
        self.mirror_control_window = None
        self.stop_event = None
        self.worker = None

    def open_mirror_control(self):
        if self.mirror_control_window is None or not self.mirror_control_window.isVisible():
            self.mirror_control_window = MirrorControlWindow()
            self.mirror_control_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self.mirror_control_window.destroyed.connect(lambda *_: setattr(self, "mirror_control_window", None))
            self.mirror_control_window.show()
        else:
            self.mirror_control_window.activateWindow()
            self.mirror_control_window.raise_()

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
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress.setValue(0)
            self.eta_label.setText("Осталось: —")
            self.signals = WorkerSignals()
            self.signals.progress.connect(self.progress.setValue)
            self.signals.log.connect(self.log_output.append)
            self.signals.plot.connect(self.display_plot)
            self.signals.finished.connect(self.on_finished)
            self.signals.eta.connect(self.eta_label.setText)
            self.stop_event = threading.Event()
            self.worker = ScannerThread(X, Y, step, t, self.device, self.signals,
                                        settle_s=0.03, flush_s=0.10, stop_event=self.stop_event)
            self.worker.start()
            self.log_output.append("Сканирование запущено.")
        except Exception as e:
            self.log_output.append(f"Ошибка запуска: {e}")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def stop_scan(self):
        if self.stop_event and not self.stop_event.is_set():
            self.log_output.append("Остановка сканирования...")
            self.stop_event.set()
            self.stop_btn.setEnabled(False)

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

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
    window.resize(900, 820)
    window.show()
    sys.exit(app.exec())
