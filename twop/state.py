from multiprocessing import Event
from lightparam import Param, ParameterTree
from lightparam.param_qt import ParametrizedQt
from scanning import (
    Scanner,
    ScanningParameters,
    ScanningState,
    ImageReconstructor,
    frame_duration,
)
from pathlib import Path
from streaming_save import StackSaver, SavingParameters
from arrayqueues.shared_arrays import ArrayQueue
from queue import Empty
from twop.objective_motor import MotorControl
from twop.external_communication import (
    ExternalCommunication,
    ExternalCommunicationSettings,
)
from twop.power_control import LaserPowerControl
from math import sqrt
from PyQt5.QtCore import QObject, pyqtSignal


class ExperimentSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "recording"
        self.n_planes = Param(1, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0))
        self.save_dir = Param("", gui=False)


class ScanningSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "scanning"
        self.aspect_ratio = Param(1.0, (0.2, 5.0))
        self.voltage = Param(3.0, (0.3, 4.0))
        self.framerate = Param(4.0)
        self.reset_shutter = Param(True)
        self.binning = Param(10, (1, 50))
        self.output_rate_khz = Param(400, (50, 2000))
        self.mystery_offset = Param(-320, (-1000, 1000))
        self.laser_power = Param(10.0, (0, 100))
        self.n_turn = Param(10, (0, 100))
        self.n_extra_init = Param(100, (0, 100))


def convert_params(st: ScanningSettings) -> ScanningParameters:
    """
    Converts the GUI scanning settings in parameters appropriate for the
    laser scanning

    """
    n_extra = -1
    i_extra = 0
    while n_extra <= 1:
        a = st.aspect_ratio
        sample_rate = st.output_rate_khz * 1000
        fps = st.framerate
        n_total = sample_rate / fps
        n_extra = st.n_extra_init + i_extra * 100
        n_turn = st.n_turn
        n_y_approx = (
            -2 * n_turn + sqrt(4 * n_turn - 4 * a * (n_extra - 2 * n_turn - n_total))
        ) / (2 * a)

        n_y = int(round(n_y_approx))
        n_x = int(round(a * n_y))

        n_extra = int(round(n_total - (n_x + 2 * n_turn) * n_y + 2 * n_turn))
        i_extra += 1

    sp = ScanningParameters(
        voltage_x=st.voltage,
        voltage_y=st.voltage,
        n_x=n_x,
        n_y=n_y,
        n_turn=n_turn,
        n_extra=n_extra,
        sample_rate_out=st.output_rate_khz * 1000,
        reset_shutter=st.reset_shutter,
        mystery_offset=st.mystery_offset,
    )
    return sp


class ExperimentState(QObject):
    sig_scanning_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.experiment_start_event = Event()
        self.scanning_settings = ScanningSettings()
        self.experiment_settings = ExperimentSettings()

        self.parameter_tree = ParameterTree()
        self.parameter_tree.add(self.scanning_settings)
        self.parameter_tree.add(self.experiment_settings)

        self.end_event = Event()
        self.external_sync = ExternalCommunication(
            self.experiment_start_event, self.end_event
        )
        self.scanner = Scanner(self.experiment_start_event, duration_queue=self.external_sync.duration_queue)
        self.scanning_parameters = None
        self.reconstructor = ImageReconstructor(
            self.scanner.data_queue, self.scanner.stop_event
        )
        self.save_queue = ArrayQueue(max_mbytes=800)
        self.saver = StackSaver(self.save_queue, self.scanner.stop_event, self.scanner.n_frames_queue)

        self.motors = dict()
        self.motors["x"] = MotorControl("COM6", axes="x")
        self.motors["y"] = MotorControl("COM6", axes="y")
        self.motors["z"] = MotorControl("COM6", axes="z")
        self.power_controller = LaserPowerControl()
        self.saving = False
        self.scanning_settings.sig_param_changed.connect(self.send_scan_params)
        self.scanning_settings.sig_param_changed.connect(self.send_save_params)
        self.external_sync.start()
        self.scanner.start()
        self.reconstructor.start()
        self.saver.start()
        self.open_setup()

    def open_setup(self):
        self.send_scan_params()

    def start_experiment(self):
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.EXPERIMENT_RUNNING
        self.scanner.parameter_queue.put(params_to_send)
        self.send_save_params()
        self.saving = True
        self.saver.start_saving.set()
        self.experiment_start_event.set()

    def close_setup(self):
        # Return Newport rotatory servo to "Not referenced" AKA stand-by state
        self.power_controller.terminate_connection()
        self.scanner.stop_event.set()
        self.end_event.set()
        self.scanner.join()
        self.reconstructor.join()
        self.external_sync.join()

    def get_image(self):
        try:
            image = -self.reconstructor.output_queue.get(timeout=0.001)
            if self.saving and self.saver.start_saving.is_set():
                self.save_queue.put(image)
            return image
        except Empty:
            return None

    def send_scan_params(self):
        self.scanning_parameters = convert_params(self.scanning_settings)
        self.power_controller.move_abs(self.scanning_settings.laser_power)
        self.scanner.parameter_queue.put(self.scanning_parameters)
        self.reconstructor.parameter_queue.put(self.scanning_parameters)
        self.sig_scanning_changed.emit()

    def send_save_params(self):
        self.saver.saving_parameter_queue.put(
            SavingParameters(
                output_dir=Path(r"C:\Users\portugueslab\Desktop\test\python"),
                plane_size=(
                    self.scanning_parameters.n_x,
                    self.scanning_parameters.n_y
                ),
                n_z=self.experiment_settings.n_planes
            )
        )
