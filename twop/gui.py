from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QSpacerItem,
)
from state import ExperimentState

import pyqtgraph as pg
import numpy as np
import qdarkstyle

from queue import Empty
from lightparam.gui import ParameterGui


class ExperimentRunner(QWidget):
    def __init__(self, experiment_settings):
        super().__init__()
        self.experiment_settings_gui = ParameterGui(experiment_settings)
        self.start_button = QPushButton("Start experiment")

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.start_button)
        self.layout().addItem(QSpacerItem(10, 10))


class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()

        # State variables
        self.state = ExperimentState()

        self.setLayout(QHBoxLayout())
        self.preview_layout = QVBoxLayout()
        self.image_viewer = pg.ImageView()
        self.preview_layout.addWidget(self.image_viewer)
        self.image_viewer.setImage(np.ones((100, 100)))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.scanner.start()
        self.first_image = True

        self.scanning_settings_gui = ParameterGui(self.scanning_settings)
        self.preview_layout.addWidget(self.scanning_settings_gui)

        self.experiment_widget = ExperimentRunner(self.state.experiment_settings)
        self.experiment_widget.start_button.clicked.connect(self.state.start_experiment)

        self.layout().addLayout(self.preview_layout)
        self.layout().addWidget(self.experiment_widget)

    def update(self):
        try:
            current_image = self.state.get_image()
            self.image_viewer.setImage(
                current_image,
                autoLevels=self.first_image,
                autoRange=self.first_image,
                autoHistogramRange=self.first_image,
            )
            self.first_image = False
        except Empty:
            pass

    def start_recording(self):
        pass

    def closeEvent(self, event) -> None:
        self.state.close_setup()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
