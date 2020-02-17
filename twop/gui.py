from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QLabel,
)
from state import ExperimentState, ScanningParameters, frame_duration

import pyqtgraph as pg
import qdarkstyle

from lightparam.gui import ParameterGui

from twop.objective_motor_sliders import MotionControlXYZ


class CalculatedParameterDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.lbl_frameinfo = QLabel()
        self.layout().addWidget(self.lbl_frameinfo)
        self.lbl_frameinfo.setMinimumHeight(120)

    def display_scanning_parameters(self, sp: ScanningParameters):
        self.lbl_frameinfo.setText(
            "Resolution: {} x {}\n".format(sp.n_x, sp.n_y)
            + "Frame duration {:03f}\n".format(frame_duration(sp))
            + "Extra pixels {}".format(sp.n_extra)
        )


class ExperimentRunner(QWidget):
    def __init__(self, experiment_settings):
        super().__init__()
        self.experiment_settings_gui = ParameterGui(experiment_settings)
        self.start_button = QPushButton("Start experiment")

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.start_button)


class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()

        # State variables
        self.state = ExperimentState()

        self.setLayout(QHBoxLayout())
        self.preview_layout = QVBoxLayout()
        self.image_viewer = pg.ImageView()
        self.preview_layout.addWidget(self.image_viewer)
        self.first_image = True

        self.scanning_settings_gui = ParameterGui(self.state.scanning_settings)
        self.scanning_calc = CalculatedParameterDisplay()

        self.preview_layout.addWidget(self.scanning_settings_gui)
        self.preview_layout.addWidget(self.scanning_calc)

        self.experiment_widget = ExperimentRunner(self.state.experiment_settings)
        self.experiment_widget.start_button.clicked.connect(self.state.start_experiment)

        self.layout().addLayout(self.preview_layout)

        self.side_layout = QVBoxLayout()

        self.side_layout.addWidget(self.experiment_widget)

        x = self.state.motors["x"]
        y = self.state.motors["y"]
        z = self.state.motors["z"]
        self.motor_control_slider = MotionControlXYZ(x, y, z)
        self.side_layout.addWidget(self.motor_control_slider)

        self.layout().addLayout(self.side_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start()

        self.state.sig_scanning_changed.connect(self.update_calc_display)

    def update(self):
        current_image = self.state.get_image()
        if current_image is None:
            return

        self.image_viewer.setImage(
            current_image,
            autoLevels=self.first_image,
            autoRange=self.first_image,
            autoHistogramRange=self.first_image,
        )
        self.first_image = False

    def update_calc_display(self):
        self.scanning_calc.display_scanning_parameters(self.state.scanning_parameters)

    def closeEvent(self, event) -> None:
        self.state.close_setup()
        self.motor_control_slider.end_session()
        event.accept()

if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
