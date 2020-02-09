from lightparam import Parametrized, Param
import lightparam.gui.precisionslider as lp
from lightparam.gui.precisionslider import PrecisionSingleSlider, SliderWidgetWithNumbers
import pyvisa
import qdarkstyle
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QGridLayout, \
    QDoubleSpinBox, QLabel, QAction
from PyQt5.QtGui import QPainter, QColor, QPen, QCloseEvent
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QPoint, QTimer
from twop.objective_motor import MotorControl


class PrecisionSingleSliderMotorControl(PrecisionSingleSlider):
    def __init__(self, *args, motor=None, axes=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.axes_pos = 0
        self.motor = motor
        if motor is not None and axes is not None:
            self.axes = self.find_axes(axes)
            self.update_pos_indicator()
        # else:
        #     raise ValueError("Specify a motor and an axes")

    def update_pos_indicator(self):
        pass  # self.axes_pos = self.motor.get_position(self.axes)  # actual position of the axes

    def find_axes(self, axes):
        if axes == 'x':
            self.axes_pos = 1
        elif axes == 'y':
            self.axes_pos = 2
        elif axes == 'z':
            self.axes_pos = 3
        return axes

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
        for triangle, label in zip([self.triangle],
                                   [1]):
            if self.mouse_status == label:
                qp.setBrush(self.highlight_color)
            else:
                qp.setBrush(self.default_color)
            qp.drawPolygon(*map(lambda point: QPointF(*point), triangle))
        # self.update_pos_indicator()
        # proj_pos = self.val_to_vis(self.axes_pos)
        print(self.pos)
        # qp.drawRect(proj_pos, triangle[0][0], 5, 3, -8)   # y pos hardcoded for the moment

    def closeEvent(self, QCloseEvent):
        print('closed')


class MotorSlider(QWidget):
    sig_changed = pyqtSignal(float)

    def __init__(self, min=0.0, max=1.0, units='mm', name=''):
        super().__init__()
        self.name = name
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.spin_val_desired_pos = QDoubleSpinBox()
        self.spin_val_actual_pos = QDoubleSpinBox()
        self.slider = PrecisionSingleSliderMotorControl(min, max)
        # self.slider.motor.set_units(units=units)
        value = self.slider.axes_pos
        self.set_home(value)
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

        self._timer_painter = QTimer(self)
        self._timer_painter.start(10)
        self._timer_painter.timeout.connect(self.update_actual_pos)

    def update_actual_pos(self):
        self.spin_val_actual_pos.setValue(self.slider.axes_pos)

    def update_values(self, val):
        self.spin_val_desired_pos.setValue(val)
        print('update_values')
        self.sig_changed.emit(val)

    def update_slider(self, new_val):
        self.slider.pos = new_val
        self.slider.update()
        # self.slider.motor.move_abs(displacement=new_val)
        self.sig_changed.emit(new_val)

    def update_external(self, new_val):
        self.slider.pos = new_val
        self.spin_val_actual_pos.setValue(new_val)
        self.slider.update()

    def move_motor(self):
        self.slider.motor.move_abs()

    def closeEvent(self, event):
        print('closed')

    def set_home(self, pos):
        self.slider.motor.define_home(pos)


app = QApplication([])
app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
# mot = MotorControl('COM1', axis='x')
win = MotorSlider(name='x', min=0, max=2)
layout = QHBoxLayout()
win.setLayout(layout)
win.show()
app.exec_()
