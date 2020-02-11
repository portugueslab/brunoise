from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from scanning import Scanner, ScanningParameters
from streaming_save import StackSaver
from state import ExperimentState

import pyqtgraph as pg
import numpy as np
from arrayqueues.shared_arrays import ArrayQueue
import qdarkstyle

from queue import Empty
from lightparam import Param, Parametrized
from lightparam.param_qt import ParametrizedQt
from lightparam.gui import ParameterGui


class ExperimentSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.n_frames = Param(10, (1, 10000))
        self.n_planes = Param(1, (1, 500))


class ScanningSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.resolution = Param(400, (40, 1024))
        self.voltage = Param(3.0, (0.3, 4.0))


class ExperimentRunner(QWidget):
    def __init__(self):
        super().__init__()
        self.experiment_settings = (
            ExperimentSettings()
        )  # TODO decouple, should not be in a GUI class
        self.experiment_settings_gui = ParameterGui(self.experiment_settings)
        self.start_button = QPushButton("Start experiment")

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.start_button)


class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()

        # State variables
        self.state = ExperimentState()

        self.scanner = Scanner(self.state.experiment_start_event)
        self.save_queue = ArrayQueue()
        self.saver = StackSaver(self.save_queue, self.scanner.stop_event)
        self.setLayout(QHBoxLayout())
        self.preview_layout = QVBoxLayout()
        self.image_viewer = pg.ImageView()
        self.preview_layout.addWidget(self.image_viewer)
        self.stop_button = QPushButton("Stop")
        self.preview_layout.addWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop)
        self.image_viewer.setImage(np.ones((100, 100)))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.scanner.start()
        self.first_image = True

        self.scanning_settings = ScanningSettings()
        self.scanning_settings_gui = ParameterGui(self.scanning_settings)
        self.preview_layout.addWidget(self.scanning_settings_gui)
        self.scanning_settings.sig_param_changed.connect(self.send_new_params)

        self.experiment_widget = ExperimentRunner()
        self.experiment_widget.start_button.clicked.connect(self.state.start_experiment)

        self.layout().addLayout(self.preview_layout)
        self.layout().addWidget(self.experiment_widget)

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
            if self.state.saving:
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
