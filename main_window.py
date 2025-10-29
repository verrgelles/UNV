from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QTabWidget

from controllers.mirrors_controller import MirrorsController
from models.mirrors_model import MirrorsModel
from ui.MirrorsControlWidget import MirrorsControlWidget

class MainWindow(QMainWindow):
    def __init__(self, logger):
        super().__init__()
        self.setWindowTitle("UNV")
        self.setWindowIcon(QIcon("assets/icon.png"))
        self.setGeometry(100, 100, 800, 600)

        self.logger = logger

        # Основной layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        tabs = QTabWidget()
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        layout.addWidget(tabs)

        # Кнопка для открытия управления зеркалами
        open_mirrors_control_btn = QPushButton("Управление зеркалами")
        open_mirrors_control_btn.clicked.connect(self.open_mirrors_control_clicked)
        layout.addWidget(open_mirrors_control_btn)

        # Инициализируем модель, вид и контроллер зеркал, но виджет не добавляем в main window
        self.mirrors_model = MirrorsModel()
        self.mirrors_view = MirrorsControlWidget()
        self.mirrors_controller = MirrorsController(self.mirrors_model, self.mirrors_view)

    def open_mirrors_control_clicked(self):
        # Показываем окно управления зеркалами (виджет)
        self.mirrors_view.show()
        self.mirrors_view.raise_()
        self.mirrors_view.activateWindow()
