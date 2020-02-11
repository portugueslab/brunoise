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
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QTimer
from twop.objective_motor import MotorControl


class PrecisionSingleSliderMotorControl(PrecisionSingleSlider):
    def __init__(self, *args, motor=None, **kwargs):
        super().__init__(*args, **kwargs)
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
            proj_pos = self.val_to_vis(self.axes_pos)
            qp.setPen(self.indicator_color)
            qp.setBrush(self.indicator_color)
            qp.drawRect(proj_pos - (3 / 2), triangle[0][1] - 2, 3, -6)


class MotorSlider(QWidget):
    sig_changed = pyqtSignal(float)
    sig_end_session = pyqtSignal()

    def __init__(self, motor=None, min=0.0, max=1.0, name=""):
        super().__init__()
        self.name = name
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.spin_val_desired_pos = QDoubleSpinBox()
        self.spin_val_actual_pos = QDoubleSpinBox()
        self.slider = PrecisionSingleSliderMotorControl(min=min, max=max, motor=motor)
        value = self.slider.axes_pos
        if value is None:
            value = (max - min) / 2
        self.spin_val_desired_pos.setValue(value)
        self.spin_val_actual_pos.setValue(value)
        self.spin_val_desired_pos.setRange(min, max)
        self.spin_val_actual_pos.setRange(min, max)
        self.spin_val_desired_pos.setDecimals(4)
        self.spin_val_actual_pos.setDecimals(4)
        self.spin_val_desired_pos.setSingleStep(0.001)
        self.spin_val_actual_pos.setSingleStep(0.001)
        self.spin_val_desired_pos.valueChanged.connect(self.update_slider)
        self.label_name = QLabel(name)
        self.label_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.grid_layout.addWidget(self.label_name, 0, 0)
        self.grid_layout.addWidget(self.spin_val_actual_pos, 0, 0)
        self.grid_layout.addWidget(self.spin_val_desired_pos, 0, 1)
        self.grid_layout.addWidget(self.slider, 1, 0, 1, 2)
        self.setLayout(self.grid_layout)
        self.slider.sig_changed.connect(self.update_values)
        self.sig_changed.connect(self.slider.motor.move_abs)
        self.sig_end_session.connect(self.slider.motor.go_home)

        self._timer_painter = QTimer(self)
        self._timer_painter.timeout.connect(self.update_actual_pos)
        self._timer_painter.start(10)

    def update_actual_pos(self):
        pos = self.slider.motor.get_position()
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

    def closeEvent(self, event):
        self.sig_end_session.emit()


app = QApplication([])
app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
mot = MotorControl("COM3", axes="x")
win = MotorSlider(name="x", min=0, max=2, motor=mot)
layout = QHBoxLayout()
win.setLayout(layout)
win.show()
app.exec_()
