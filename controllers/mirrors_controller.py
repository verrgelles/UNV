from PyQt6.QtCore import QObject


class MirrorsController(QObject):
    def __init__(self, model, widget):
        super().__init__()
        self.model = model
        self.widget = widget

        # Подключаем UI-сигналы к обработчикам
        self.widget.goUpRequested.connect(self.move_up)
        self.widget.goDownRequested.connect(self.move_down)
        self.widget.goLeftRequested.connect(self.move_left)
        self.widget.goRightRequested.connect(self.move_right)
        self.widget.goCenterRequested.connect(self.move_center)
        self.widget.goToPositionRequested.connect(self.move_to)

        # Подключаем модельные сигналы к UI
        self.model.positionChanged.connect(self.widget.set_position_fields)
        self.model.errorOccurred.connect(self.show_error)

        # Инициализация
        self.model.connect()

    def move_to(self, x: float, y: float):
        self.model.move_to([x, y])

    def move_up(self):
        x, y = self.widget.get_current_coords()
        _, step_y = self.widget.get_step()
        self.model.move_to([x, y + step_y])

    def move_down(self):
        x, y = self.widget.get_current_coords()
        _, step_y = self.widget.get_step()
        self.model.move_to([x, y - step_y])

    def move_left(self):
        x, y = self.widget.get_current_coords()
        step_x, _ = self.widget.get_step()
        self.model.move_to([x - step_x, y])

    def move_right(self):
        x, y = self.widget.get_current_coords()
        step_x, _ = self.widget.get_step()
        self.model.move_to([x + step_x, y])

    def move_center(self):
        self.model.move_to(self.model.center)

    def show_error(self, message: str):
        print(f"[Mirror Error] {message}")  # Можно заменить на QMessageBox
