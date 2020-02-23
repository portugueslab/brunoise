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
    QFileDialog,
)
from state import ExperimentState, ScanningParameters, frame_duration
from twop.objective_motor_sliders import MotionControlXYZ

import pyqtgraph as pg
import qdarkstyle
from pathlib import Path

from lightparam.gui import ParameterGui


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
            + "Frame duration {:.3f}\n".format(frame_duration(sp))
            + "Extra pixels {}\n".format(sp.n_extra)
            + "Frame scanning frequency {:.2f}Hz".format(
                sp.sample_rate_out / (2 * (sp.n_x + sp.n_turn))
            )
        )


class ExperimentControl(QWidget):
    def __init__(self, state: ExperimentState):
        super().__init__()
        self.state = state
        self.experiment_settings_gui = ParameterGui(state.experiment_settings)
        self.save_location_button = QPushButton()
        self.set_locationbutton()
        self.save_location_button.clicked.connect(self.set_save_location)
        self.startstop_button = QPushButton()
        self.set_saving()
        self.stack_progress = QProgressBar()
        self.plane_progress = QProgressBar()
        self.plane_progress.setFormat("Frame %v of %m")
        self.stack_progress.setFormat("Plane %v of %m")
        self.startstop_button.clicked.connect(self.toggle_start)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.save_location_button)
        self.layout().addWidget(self.startstop_button)
        self.layout().addWidget(self.plane_progress)
        self.layout().addWidget(self.stack_progress)

    def set_saving(self):
        self.startstop_button.setText("Start recording")
        self.startstop_button.setStyleSheet(
            "background-color:#1d824f; border-color:#1c9e66"
        )

    def set_notsaving(self):
        self.startstop_button.setText("Stop recording")
        self.startstop_button.setStyleSheet(
            "background-color:#82271d; border-color:#9e391c"
        )

    def toggle_start(self):
        if self.state.saving:
            self.state.end_experiment(force=True)
            self.set_saving()
        else:
            if self.state.start_experiment():
                self.set_notsaving()

    def set_locationbutton(self):
        pathtext = self.state.experiment_settings.save_dir
        # check if there is a stack in this location
        if (Path(pathtext) / "original" / "stack_metadata.json").is_file():
            self.save_location_button.setText("Overwrite " + pathtext)
            self.save_location_button.setStyleSheet(
                "background-color:#b5880d; border-color:#fcc203"
            )
        else:
            self.save_location_button.setText("Save in " + pathtext)
            self.save_location_button.setStyleSheet("")

    def set_save_location(self):
        save_dir = QFileDialog.getExistingDirectory()
        self.state.experiment_settings.save_dir = save_dir
        self.set_locationbutton()

    def update(self):
        sstatus = self.state.get_save_status()
        if sstatus is not None:
            self.plane_progress.setMaximum(sstatus.target_params.n_t)
            self.plane_progress.setValue(sstatus.i_t)
            self.stack_progress.setMaximum(sstatus.target_params.n_z)
            self.stack_progress.setValue(sstatus.i_z)
        if not self.state.saving:
            self.set_saving()


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
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
