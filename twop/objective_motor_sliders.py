from lightparam import Parametrized, Param
import lightparam.gui.precisionslider as lp

from lightparam.gui.precisionslider import (
    PrecisionSingleSlider,
    SliderWidgetWithNumbers,
)
import pyvisa
import qdarkstyle
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QGridLayout,
    QDoubleSpinBox,
    QLabel,
    QGraphicsOpacityEffect,
)
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QPoint

from twop.objective_motor import MotorControl


class MotorSlider(PrecisionSingleSlider):
    def __init__(self, motor=None, axes=None):
        super().__init__()
        self.axes_pos = None
        self.motor = motor
        if motor is not None and axes is not None:
            self.axes = self.find_axes(axes)
            self.update_pos_indicator()
        # else:
        #     raise ValueError("Specify a motor and an axes")

    def update_pos_indicator(self):
        self.axes_pos = self.motor.update_position(
            self.axes
        )  # actual position of the axes

    def find_axes(self, axes):
        if axes == "x":
            self.axes_pos = 1
        elif axes == "y":
            self.axes_pos = 2
        elif axes == "z":
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

        for triangle, label in zip([self.triangle], [1]):
            if self.mouse_status == label:
                qp.setBrush(self.highlight_color)
            else:
                qp.setBrush(self.default_color)

            qp.drawPolygon(*map(lambda point: QPointF(*point), triangle))

        # self.update_pos_indicator()
        # proj_pos = self.val_to_vis(self.axes_pos)
        print(self.pos, lv)
        # qp.drawRect(triangle[0][0], 5, 3, -8)   # y pos hardcoded for the moment


app = QApplication([])
app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
win = QWidget()
layout = QHBoxLayout()
win.setLayout(layout)
# mot = MotorControl('COM1')
slider_1 = MotorSlider()
layout.addWidget(slider_1)
win.show()
app.exec_()
