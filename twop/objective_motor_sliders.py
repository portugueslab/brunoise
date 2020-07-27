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
from enum import Enum
from queue import Empty

class MovementType(Enum):
    absolute = True
    relative = False


class MotionControlXYZ(QWidget):
    def __init__(self, input_queues, output_queues):
        super().__init__()
        self.setLayout(QGridLayout())

        for axis in input_queues.keys():
            wid = MotorSlider(name=axis,
                              input_queue=input_queues[axis],
                              output_queue=output_queues[axis]
                              )
            self.layout().addWidget(wid)


class PrecisionSingleSliderMotorControl(PrecisionSingleSlider):
    def __init__(self, *args, input_queue=None, output_queue=None, pos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos = pos
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.axes_pos = 0
        self.indicator_color = QColor(178, 0, 0)

    def drawWidget(self, qp):
        size = self.size()
        w = size.width()
        h = size.height()
        pt = h // 2
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

    def __init__(self, input_queue=None, output_queue=None, move_limit_low=-3, move_limit_high=3, name=""):
        super().__init__()
        self.name = name
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.spin_val_desired_pos = QDoubleSpinBox()
        self.spin_val_actual_pos = QDoubleSpinBox()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.mov_type = MovementType(False)
        value = get_next_entry(self.output_queue)
        min_range = value + move_limit_low
        max_range = value + move_limit_high
        self.position = value

        self.slider = PrecisionSingleSliderMotorControl(
            default_value=value, min=min_range, max=max_range, pos=value, input_queue=None, output_queue=None,
        )
        for spin_val in [self.spin_val_actual_pos, self.spin_val_desired_pos]:
            spin_val.setRange(min_range, max_range)
            spin_val.setDecimals(4)
            spin_val.setSingleStep(0.001)
            spin_val.setValue(value)
            spin_val.setMaximumWidth(80)

        self.spin_val_actual_pos.setEnabled(False)
        self.spin_val_desired_pos.valueChanged.connect(self.update_slider)
        self.label_name = QLabel("<h3>" + name + r"<\h3>")
        self.label_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_name.setMaximumWidth(16)
        self.grid_layout.addWidget(self.label_name, 0, 0, 2, 1)
        self.grid_layout.addWidget(self.slider, 0, 1, 2, 1)
        self.grid_layout.addWidget(self.spin_val_actual_pos, 0, 2)
        self.grid_layout.addWidget(self.spin_val_desired_pos, 1, 2)

        self.setLayout(self.grid_layout)
        self.slider.sig_changed.connect(self.update_values)

        self._timer_painter = QTimer(self)
        self._timer_painter.timeout.connect(self.update_actual_pos)
        self._timer_painter.start()

    def update_actual_pos(self):
        while True:
            try:
                pos = self.output_queue.get(timeout=0.001)
            except Empty:
                break
            self.spin_val_actual_pos.setValue(pos)
            self.slider.axes_pos = pos
            self.position = pos

    def update_values(self, new_val):
        self.spin_val_desired_pos.setValue(new_val)
        displacement = new_val - self.position
        print("update_values", displacement)
        self.input_queue.put((displacement, self.mov_type))

    def update_slider(self, new_val):
        self.slider.pos = new_val
        self.slider.update()
        displacement = new_val - self.position
        print("update_slider", displacement)
        self.input_queue.put((displacement, self.mov_type))

    def update_external(self, new_val):
        self.slider.pos = new_val
        self.spin_val_actual_pos.setValue(new_val)
        self.slider.update()


def get_next_entry(queue):
    out = None
    while out is None:
        try:
            out = queue.get(timeout=0.001)
        except Empty:
            pass
    return out

if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    layout = QHBoxLayout()
    win = MotionControlXYZ(None, None, None)
    win.show()
    app.exec_()