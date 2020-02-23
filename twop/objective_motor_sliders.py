from lightparam.gui.precisionslider import PrecisionSingleSlider
import qdarkstyle
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QDoubleSpinBox,
    QLabel,
)

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QTimer


class MotionControlXYZ(QWidget):
    def __init__(self, mot_x, mot_y, mot_z):
        super().__init__()
        self.setLayout(QGridLayout())

        self.win_x = MotorSlider(name="x", motor=mot_x)
        self.layout().addWidget(self.win_x)

        self.win_y = MotorSlider(name="y", motor=mot_y)
        self.layout().addWidget(self.win_y)

        self.win_z = MotorSlider(name="z", motor=mot_z)
        self.layout().addWidget(self.win_z)


class PrecisionSingleSliderMotorControl(PrecisionSingleSlider):
    def __init__(self, *args, motor=None, pos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos = pos
        self.motor = motor
        self.axes_pos = 0
        self.indicator_color = QColor(178, 0, 0)

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()
        pt = self.padding_top
        ps = self.padding_side
        qp.setPen(QColor(100, 100, 100))
        qp.drawLine(ps, pt, w - ps, pt)
        qp.setPen(Qt.NoPen)
        qp.setBrush(self.default_color)
        lv = self.val_to_vis(self.pos)
        self.triangle = self._equilateral_triangle_points((lv, pt))
        for triangle, label in zip([self.triangle], [1]):
            if self.mouse_status == label:
                qp.setBrush(self.highlight_color)
            else:
                qp.setBrush(self.default_color)
            qp.drawPolygon(*map(lambda point: QPointF(*point), triangle))
            proj_pos = int(self.val_to_vis(self.axes_pos))
            qp.setPen(self.indicator_color)
            qp.setBrush(self.indicator_color)
            qp.drawRect(proj_pos - (0.5 / 2), triangle[0][1] - 2, 0.5, -6)


class MotorSlider(QWidget):
    sig_changed = pyqtSignal(float)
    sig_end_session = pyqtSignal()

    def __init__(self, motor=None, move_limit_low=-3, move_limit_high=3, name=""):
        super().__init__()
        self.name = name
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.spin_val_desired_pos = QDoubleSpinBox()
        self.spin_val_actual_pos = QDoubleSpinBox()

        value = 0  # motor.home_pos
        min_range = value + move_limit_low
        max_range = value + move_limit_high

        self.slider = PrecisionSingleSliderMotorControl(
            default_value=value, min=min_range, max=max_range, pos=value, motor=motor
        )
        for spin_val in [self.spin_val_actual_pos, self.spin_val_desired_pos]:
            spin_val.setRange(min_range, max_range)
            spin_val.setDecimals(4)
            spin_val.setSingleStep(0.001)
            spin_val.setValue(value)

        self.spin_val_actual_pos.setEnabled(False)
        self.spin_val_desired_pos.valueChanged.connect(self.update_slider)
        self.label_name = QLabel(name)
        self.label_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.grid_layout.addWidget(self.label_name, 0, 0, 2, 1)
        self.grid_layout.addWidget(self.slider, 0, 1, 2, 1)
        self.grid_layout.addWidget(self.spin_val_actual_pos, 0, 2)
        self.grid_layout.addWidget(self.spin_val_desired_pos, 1, 2)

        self.setLayout(self.grid_layout)
        self.slider.sig_changed.connect(self.update_values)
        self.sig_changed.connect(self.slider.motor.move_abs)

        self._timer_painter = QTimer(self)
        self._timer_painter.timeout.connect(self.update_actual_pos)
        self._timer_painter.start()

    def update_actual_pos(self):
        if self.slider.motor.connection is True:
            pos = self.slider.motor.get_position()
            if pos is not None:
                self.spin_val_actual_pos.setValue(pos)
                self.slider.axes_pos = pos

    def update_values(self, val):
        self.spin_val_desired_pos.setValue(val)
        self.sig_changed.emit(val)

    def update_slider(self, new_val):
        self.slider.pos = new_val
        self.slider.update()
        self.sig_changed.emit(new_val)

    def update_external(self, new_val):
        self.slider.pos = new_val
        self.spin_val_actual_pos.setValue(new_val)
        self.slider.update()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    layout = QHBoxLayout()
    win = MotionControlXYZ(None, None, None)
    win.show()
    app.exec_()
