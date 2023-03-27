from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QDockWidget,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QFileDialog,
    QCheckBox,
)
from state import ExperimentState, ScanningParameters, frame_duration
from brunoise.objective_motor_sliders import MotionControlXYZ

import pyqtgraph as pg
import qdarkstyle
from pathlib import Path
import numpy as np

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
            + "Estimated frame duration {:.3f}\n".format(frame_duration(sp))
            + "Extra pixels {}\n".format(sp.n_extra)
            + "Line scanning frequency {:.2f}Hz".format(
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
        self.chk_pause = QCheckBox("Pause after experiment")
        self.stack_progress = QProgressBar()
        self.plane_progress = QProgressBar()
        self.plane_progress.setFormat("Frame %v of %m")
        self.stack_progress.setFormat("Plane %v of %m")
        self.startstop_button.clicked.connect(self.toggle_start)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.experiment_settings_gui)
        self.layout().addWidget(self.save_location_button)
        self.layout().addWidget(self.startstop_button)
        self.layout().addWidget(self.chk_pause)
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
            self.state.pause_after = self.chk_pause.isChecked()
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
        self.image_viewer = pg.ImageView()
        self.image_viewer.ui.roiBtn.hide()
        self.image_viewer.ui.menuBtn.hide()
        self.chk_green = QCheckBox("Green Channel")
        self.chk_green.setChecked(True)
        self.chk_red = QCheckBox("Red Channel")
        self.chk_roi = QCheckBox("draw an roi")
        self.chk_roi.toggled.connect(self.draw_roi)

        self.layout = QGridLayout()
        self.layout.addWidget(self.image_viewer, 0, 0, 1, 2)
        self.layout.addWidget(self.chk_green, 1, 0)
        self.layout.addWidget(self.chk_red, 2, 0)
        self.layout.addWidget(self.chk_roi, 1, 1)
        self.setLayout(self.layout)

        self.first_image = True
        self.color_modality_in_use = "g"
        self.modality_to_display = "g"
        self.levelMode_in_use = "mono"
        self.levelMode_to_display = "mono"

        self.roi = None

    def update(self) -> None:
        current_images = self.state.get_image()

        if current_images is None:
            return

        if not(self.chk_green.isChecked()) and not(self.chk_red.isChecked()):
            self.chk_green.setChecked(True)
            self.modality_to_display = "g"
            self.levelMode_to_display = "mono"
        if self.chk_green.isChecked() and not(self.chk_red.isChecked()):
            current_image = current_images[0, :, :]
            self.modality_to_display = "g"
            self.levelMode_to_display = "mono"
        elif self.chk_red.isChecked() and not(self.chk_green.isChecked()):
            current_image = current_images[1, :, :]
            self.modality_to_display = "r"
            self.levelMode_to_display = "mono"
        elif self.chk_red.isChecked() and self.chk_green.isChecked():
            current_image = np.stack([current_images[1, :, :], current_images[0, :, :], current_images[1, :, :]], -1)
            self.modality_to_display = "gr"
            self.levelMode_to_display = "rgba"

        if self.color_modality_in_use != self.modality_to_display:
            self.first_image = True
            self.color_modality_in_use = self.modality_to_display

        if self.levelMode_in_use != self.levelMode_to_display:
            self.levelMode_in_use = self.levelMode_to_display

        self.image_viewer.setImage(
            current_image,
            autoLevels=self.first_image,
            autoRange=self.first_image,
            autoHistogramRange=self.first_image,
            levelMode=self.levelMode_in_use
        )
        self.first_image = False

        if self.roi is None:
            self.state.roi_settings.roi_write_signals = np.empty(0)
        else:
            self.state.roi_settings.roi_write_signals = self.get_roi_write_signals()

    def draw_roi(self):
        if self.chk_roi.isChecked():
            self.roi = pg.RectROI((0, 0), (30, 30), removable=True)
            self.image_viewer.addItem(self.roi)
        else:
            self.image_viewer.removeItem(self.roi)
            self.roi = None

    def get_roi_write_signals(self):
        vol_x = self.state.scanning_parameters.voltage_x
        vol_y = self.state.scanning_parameters.voltage_y
        n_x = self.state.scanning_parameters.n_x
        n_y = self.state.scanning_parameters.n_y
        x_array = np.array([np.linspace(-vol_x, vol_x, n_x) for _ in range(n_x)]).T
        y_array = np.array([np.linspace(-vol_y, vol_y, n_y) for _ in range(n_y)])
        result = self.roi.getArrayRegion(np.stack([x_array, y_array], axis=0), self.image_viewer.imageItem, axes=(1, 2))
        return result.reshape(2, -1)


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


class ScanningWidget(QWidget):
    def __init__(self, state: ExperimentState):
        self.state = state
        super().__init__()
        self.scanning_layout = QVBoxLayout()

        self.scanning_settings_gui = ParameterGui(self.state.scanning_settings)
        self.scanning_calc = CalculatedParameterDisplay()
        self.pause_button = QPushButton()
        self.pause_button.clicked.connect(self.toggle_pause)

        self.scanning_layout.addWidget(self.scanning_settings_gui)
        self.scanning_layout.addWidget(self.scanning_calc)
        self.scanning_layout.addWidget(self.pause_button)
        self.setLayout(self.scanning_layout)

        self.state.sig_scanning_changed.connect(self.update_display)
        self.update_button()

    def update_display(self):
        self.scanning_calc.display_scanning_parameters(self.state.scanning_parameters)

        self.pause_button.setEnabled(self.state.scanning_parameters.pause)

    def update_button(self):
        if self.state.paused:
            self.pause_button.setText("Resume")
        else:
            self.pause_button.setText("Pause")

    def toggle_pause(self):
        if self.state.paused:
            self.state.restart_scanning()
        else:
            self.state.pause_scanning()
        self.update_button()


class RoiWidget(QWidget):
    def __init__(self, state: ExperimentState):
        self.state = state
        super().__init__()
        self.roi_layout = QVBoxLayout()
        self.roi_settings_gui = ParameterGui(self.state.roi_settings)
        self.roi_layout.addWidget(self.roi_settings_gui)
        self.setLayout(self.roi_layout)


class TwopViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # State variables
        self.state = ExperimentState()

        self.image_display = ViewingWidget(self.state)
        self.setCentralWidget(self.image_display)

        self.scanning_widget = ScanningWidget(self.state)
        self.roi_widget = RoiWidget(self.state)
        self.experiment_widget = ExperimentControl(self.state)

        self.motor_control_slider = MotionControlXYZ(self.state.motors)

        self.addDockWidget(
            Qt.LeftDockWidgetArea,
            DockedWidget(widget=self.scanning_widget, title="Scanning settings"),
        )
        self.addDockWidget(
            Qt.LeftDockWidgetArea,
            DockedWidget(widget=self.roi_widget, title="Roi scanning"),
        )
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
        self.timer.start()

    def update(self):
        self.image_display.update()
        self.experiment_widget.update()

    def closeEvent(self, event) -> None:
        self.state.close_setup()
        event.accept()
