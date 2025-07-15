# ui/mirrors_widget.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QGridLayout, QLabel, QDoubleSpinBox

class MirrorsControlWidget(QWidget):
    goUpRequested = pyqtSignal()
    goDownRequested = pyqtSignal()
    goLeftRequested = pyqtSignal()
    goRightRequested = pyqtSignal()
    goCenterRequested = pyqtSignal()
    goToPositionRequested = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление зеркалами")
        self.setWindowIcon(QIcon("./assets/icon.png"))
        self.setFixedSize(300, 300)

        layout = QVBoxLayout()

        coords_layout = QGridLayout()

        x_coord = QLabel("Координата x")
        y_coord = QLabel("Координата y")
        self.x_coord_field = QDoubleSpinBox()
        self.y_coord_field = QDoubleSpinBox()

        self._setup_spinbox(self.x_coord_field, -35, 35, 0.001)
        self._setup_spinbox(self.y_coord_field, -35, 35, 0.001)

        x_step = QLabel("Шаг x")
        y_step = QLabel("Шаг y")
        self.x_step_field = QDoubleSpinBox()
        self.y_step_field = QDoubleSpinBox()

        self._setup_spinbox(self.x_step_field, 0.01, 100, 0.001)
        self._setup_spinbox(self.y_step_field, 0.01, 100, 0.001)

        coords_layout.addWidget(x_coord, 0, 0)
        coords_layout.addWidget(y_coord, 0, 1)
        coords_layout.addWidget(self.x_coord_field, 1, 0)
        coords_layout.addWidget(self.y_coord_field, 1, 1)
        coords_layout.addWidget(x_step, 2, 0)
        coords_layout.addWidget(y_step, 2, 1)
        coords_layout.addWidget(self.x_step_field, 3, 0)
        coords_layout.addWidget(self.y_step_field, 3, 1)

        move_layout = QGridLayout()
        self._add_direction_buttons(move_layout)

        self.go_button = QPushButton("Установить зеркала")
        self.go_button.clicked.connect(self._emit_go_to_position)

        layout.addLayout(coords_layout)
        layout.addLayout(move_layout)
        layout.addWidget(self.go_button)

        self.setLayout(layout)

    def _setup_spinbox(self, spinbox, min_val, max_val, step):
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(step)
        spinbox.setDecimals(3)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    def _add_direction_buttons(self, layout):
        btn_up = QPushButton("↑")
        btn_down = QPushButton("↓")
        btn_left = QPushButton("←")
        btn_right = QPushButton("→")
        btn_center = QPushButton("◯")

        btn_up.clicked.connect(self.goUpRequested.emit)
        btn_down.clicked.connect(self.goDownRequested.emit)
        btn_left.clicked.connect(self.goLeftRequested.emit)
        btn_right.clicked.connect(self.goRightRequested.emit)
        btn_center.clicked.connect(self.goCenterRequested.emit)

        layout.addWidget(btn_up, 0, 1)
        layout.addWidget(btn_left, 1, 0)
        layout.addWidget(btn_center, 1, 1)
        layout.addWidget(btn_right, 1, 2)
        layout.addWidget(btn_down, 2, 1)

    def _emit_go_to_position(self):
        self.goToPositionRequested.emit(self.x_coord_field.value(), self.y_coord_field.value())

    def set_position_fields(self, x: float, y: float):
        self.x_coord_field.setValue(x)
        self.y_coord_field.setValue(y)

    def get_step(self):
        return self.x_step_field.value(), self.y_step_field.value()

    def get_current_coords(self):
        return self.x_coord_field.value(), self.y_coord_field.value()
