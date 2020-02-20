from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QDockWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
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


class ExperimentControl(QWidget):
    def __init__(self, state: ExperimentState):
        super().__init__()
        self.state = state
        self.experiment_settings_gui = ParameterGui(state.experiment_settings)
        self.startstop_button = QPushButton("Start recording")
        self.stack_progress = QProgressBar()
        self.plane_progress = QProgressBar()
        self.plane_progress.setFormat("Frame %v of %m")
        self.stack_progress.setFormat("Plane %v of %m")
        self.startstop_button.clicked.connect(self.toggle_start)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.startstop_button)
        self.layout().addWidget(self.plane_progress)
        self.layout().addWidget(self.stack_progress)

    def toggle_start(self):
        if self.state.saving:
            self.state.end_experiment(force=True)
            self.startstop_button.setText("Start recording")
        else:
            if self.state.start_experiment():
                self.startstop_button.setText("Stop recording")

    def update(self):
        sstatus = self.state.get_save_status()
        if sstatus is not None:
            self.plane_progress.setMaximum(sstatus.target_params.n_t)
            self.plane_progress.setValue(sstatus.i_t)
            self.stack_progress.setMaximum(sstatus.target_params.n_z)
            self.stack_progress.setValue(sstatus.i_z)
        if self.state.saving == False:
            self.startstop_button.setText("Start recording")


class ViewingWidget(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.setLayout(QVBoxLayout())
        self.image_viewer = pg.ImageView()
        self.layout().addWidget(self.image_viewer)
        self.first_image = True

    def update(self) -> None:
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


class DockedWidget(QDockWidget):
    def __init__(self, widget=None, layout=None, title=""):
        super().__init__()
        if widget is not None:
            self.setWidget(widget)
        else:
            self.setWidget(QWidget())
            self.widget().setLayout(layout)
        if title != "":
            self.setWindowTitle(title)


class TwopViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # State variables
        self.state = ExperimentState()

        self.image_display = ViewingWidget(self.state)
        self.setCentralWidget(self.image_display)

        self.scanning_layout = QVBoxLayout()

        self.scanning_settings_gui = ParameterGui(self.state.scanning_settings)
        self.scanning_calc = CalculatedParameterDisplay()

        self.scanning_layout.addWidget(self.scanning_settings_gui)
        self.scanning_layout.addWidget(self.scanning_calc)

        self.scanning_dock = DockedWidget(
            layout=self.scanning_layout, title="Scanning settings"
        )

        self.experiment_widget = ExperimentControl(self.state)

        x = self.state.motors["x"]
        y = self.state.motors["y"]
        z = self.state.motors["z"]
        self.motor_control_slider = MotionControlXYZ(x, y, z)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.scanning_dock)
        self.addDockWidget(
            Qt.RightDockWidgetArea,
            DockedWidget(widget=self.motor_control_slider, title="Stage control"),
        )
        self.addDockWidget(
            Qt.RightDockWidgetArea,
            DockedWidget(widget=self.experiment_widget, title="Experiment running"),
        )

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.timeout.connect(self.experiment_widget.update)
        self.timer.start()

        self.state.sig_scanning_changed.connect(self.update_calc_display)

    def update(self):
        self.image_display.update()
        self.experiment_widget.update()

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
