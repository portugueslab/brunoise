from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from scanning import Scanner, ScanningParameters
from streaming_save import StackSaver

import pyqtgraph as pg
import numpy as np
from arrayqueues.shared_arrays import ArrayQueue
import qdarkstyle

from queue import Empty
from lightparam import Param, Parametrized
from lightparam.param_qt import ParametrizedQt
from lightparam.gui import ParameterGui


class ExperimentSettings(Parametrized):
    def __init__(self):
        super().__init__()
        self.n_frames = Param(10, (1, 10000))
        self.n_planes = Param(1, (1, 500))


class ScanningSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.resolution = Param(400, (40, 1024))
        self.voltage = Param(3.0, (0.3, 4.0))


class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.scanner = Scanner()
        self.save_queue = ArrayQueue()
        self.saver = StackSaver(self.save_queue, self.scanner.stop_event)
        self.setLayout(QVBoxLayout())
        self.image_viewer = pg.ImageView()
        self.layout().addWidget(self.image_viewer)
        self.stop_button = QPushButton("Stop")
        self.layout().addWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop)
        self.image_viewer.setImage(np.ones((100, 100)))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.scanner.start()
        self.first_image = True

        self.scanning_settings = ScanningSettings()
        self.scanning_settings_gui = ParameterGui(self.scanning_settings)
        self.layout().addWidget(self.scanning_settings_gui)
        self.scanning_settings.sig_param_changed.connect(self.send_new_params)

        # State variables
        self.saving = False

    def update(self):
        try:
            current_image = -self.scanner.data_queue.get(timeout=0.001)
            self.image_viewer.setImage(
                current_image,
                autoLevels=self.first_image,
                autoRange=self.first_image,
                autoHistogramRange=self.first_image,
            )
            self.first_image = False
            if self.saving:
                self.save_queue.put(current_image)
        except Empty:
            pass

    def start_recording(self):
        pass

    def stop(self):
        self.scanner.stop_event.set()

    def send_new_params(self):
        self.scanner.parameter_queue.put(
            ScanningParameters(
                voltage_x=self.scanning_settings.voltage,
                voltage_y=self.scanning_settings.voltage,
                n_x=self.scanning_settings.resolution,
                n_y=self.scanning_settings.resolution,
            )
        )


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
