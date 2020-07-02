from multiprocessing import Event, Queue
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
from streaming_save import StackSaver, SavingParameters, SavingStatus
from arrayqueues.shared_arrays import ArrayQueue
from queue import Empty
from twop.objective_motor import MotorControl
from twop.external_communication import ZMQcomm
from twop.power_control import LaserPowerControl
from math import sqrt
from PyQt5.QtCore import QObject, pyqtSignal
from typing import Optional
from enum import Enum
from time import sleep
from sequence_diagram import SequenceDiagram
from dataclasses import dataclass


class ReferenceSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "reference"
        self.n_frames_ref = Param(10, (1, 500))
        self.extra_planes = Param(1, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0), unit="um")
        self.xy_th = Param(5.0, (0.1, 20.0), unit="um")
        self.z_th = Param(self.dz, (self.dz, self.dz * 4), unit="um")
        self.n_frames_exp = Param(5, (1, 500))


@dataclass
class ReferenceParameters:
    n_frames_ref: int = 10
    extra_planes: int = 10
    dz: float = 1.0
    xy_th: float = 5
    z_th: float = 1
    n_frames_exp: int = 5


def convert_reference_params(st: ReferenceSettings) -> ReferenceParameters:
    n_frames_ref = st.n_frames_ref
    extra_planes = st.extra_planes
    xy_th = st.xy_th
    dz = st.dz
    z_th = st.z_th
    n_frames_exp = st.n_frames_exp
    rp = ReferenceParameters(n_frames_ref=n_frames_ref,
                             extra_planes=extra_planes,
                             dz=dz,
                             xy_th=xy_th,
                             z_th=z_th,
                             n_frames_exp=n_frames_exp
                             )

    return rp


class ExperimentSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "recording"
        self.n_planes = Param(1, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0), unit="um")
        self.save_dir = Param(r"C:\Users\portugueslab\Desktop\test\python", gui=False)


class ScanningSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "scanning"
        self.aspect_ratio = Param(1.0, (0.2, 5.0))
        self.voltage = Param(3.0, (0.2, 4.0))
        self.framerate = Param(2.0, (0.1, 10.0))
        self.reset_shutter = Param(False)
        self.binning = Param(10, (1, 50))
        self.output_rate_khz = Param(400, (50, 2000))
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

    mystery_offset = -int(round(st.output_rate_khz * 0.8))
    voltage_max = st.voltage
    if st.aspect_ratio >= 1:
        voltage_x = voltage_max
        voltage_y = voltage_x / st.aspect_ratio
    else:
        voltage_x = voltage_max * st.aspect_ratio
        voltage_y = voltage_max

    sp = ScanningParameters(
        voltage_x=voltage_x,
        voltage_y=voltage_y,
        n_x=n_x,
        n_y=n_y,
        n_turn=n_turn,
        n_extra=n_extra,
        sample_rate_out=sample_rate,
        reset_shutter=st.reset_shutter,
        mystery_offset=mystery_offset,
    )
    return sp


class ExperimentState(QObject):
    sig_scanning_changed = pyqtSignal()

    def __init__(self, diagnostics=False):
        super().__init__()
        if diagnostics:
            self.sequence_queue = Queue()
            self.sequence_diagram = SequenceDiagram(self.sequence_queue, "main")

        self.experiment_start_event = Event()
        self.scanning_settings = ScanningSettings()
        self.experiment_settings = ExperimentSettings()
        self.reference_settings = ReferenceSettings()
        self.pause_after = False

        self.parameter_tree = ParameterTree()
        self.parameter_tree.add(self.scanning_settings)
        self.parameter_tree.add(self.experiment_settings)

        self.end_event = Event()
        self.external_sync = ZMQcomm()
        self.duration_queue = Queue()
        self.scanner = Scanner(
            self.experiment_start_event, duration_queue=self.duration_queue
        )
        self.scanning_parameters = None
        self.reconstructor = ImageReconstructor(
            self.scanner.data_queue, self.scanner.stop_event
        )
        self.save_queue = ArrayQueue(max_mbytes=800)
        self.reference_event = Event()
        self.reference_params = None
        self.reference_queue = ArrayQueue(max_mbytes=800)
        self.saver = StackSaver(
            self.scanner.stop_event, self.save_queue, self.scanner.n_frames_queue, self.reference_event,
            self.reference_queue
        )
        self.save_status: Optional[SavingStatus] = None

        self.motors = dict()
        self.motors["x"] = MotorControl("COM6", axes="x")
        self.motors["y"] = MotorControl("COM6", axes="y")
        self.motors["z"] = MotorControl("COM6", axes="z")
        self.power_controller = LaserPowerControl()
        self.scanning_settings.sig_param_changed.connect(self.send_scan_params)
        self.scanning_settings.sig_param_changed.connect(self.send_save_params)
        self.reference_settings.sig_param_changed.connect(self.send_reference_params)
        self.experiment_settings.sig_param_changed.connect(self.send_reference_params)
        self.scanner.start()
        self.reconstructor.start()
        self.saver.start()
        self.open_setup()

        self.paused = False

    @property
    def saving(self):
        return self.saver.saving_signal.is_set()

    def open_setup(self):
        self.send_scan_params()
        self.send_reference_params()

    def start_experiment(self, first_plane=True):
        if not self.reference_event.is_set():
            duration = self.external_sync.send(self.parameter_tree.serialize())
            if duration is None:
                self.restart_scanning()
                return False
            self.duration_queue.put(duration)
        else:
            duration = self.reference_params.n_frames_ref * (1 / self.scanning_settings.framerate)
            self.duration_queue.put(duration)
            if first_plane:
                self.move_stage_reference()
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.EXPERIMENT_RUNNING
        self.scanner.parameter_queue.put(params_to_send)
        if first_plane:
            self.send_save_params()
            self.saver.saving_signal.set()
        self.experiment_start_event.set()
        print("start experiment with duration of", duration)
        return True

    def end_experiment(self, force=False):
        self.experiment_start_event.clear()

        if not force and self.save_status.i_z + 1 < self.save_status.target_params.n_z:
            self.advance_plane()
        else:
            self.saver.saving_signal.clear()
            if self.reference_event.is_set():
                self.move_stage_reference(first=False)
                self.reference_event.clear()
            if self.pause_after:
                self.pause_scanning()
            else:
                self.restart_scanning()

    def restart_scanning(self):
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.PREVIEW
        self.scanner.parameter_queue.put(params_to_send)
        self.paused = False

    def pause_scanning(self):
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.PAUSED
        self.scanner.parameter_queue.put(params_to_send)
        self.paused = True

    def advance_plane(self):
        self.motors["z"].move_rel(self.experiment_settings.dz / 1000)
        print("plane advanced by by", self.experiment_settings.dz)
        sleep(0.2)
        self.start_experiment(first_plane=False)

    def move_stage_reference(self, first=True):
        if first:
            mic_to_move = - self.reference_params.extra_planes * self.experiment_settings.dz
        else:
            mic_to_move = - (self.reference_params.extra_planes +
                             self.experiment_settings.n_planes - 1) * self.experiment_settings.dz
        print("moving stage up by", mic_to_move)
        self.motors["z"].move_rel(mic_to_move / 1000)
        sleep(0.2)

    def close_setup(self):
        """ Cleanup on programe close:
        end all parallel processes, close all communication channels

        """
        for motor in self.motors.values():
            motor.end_session()
        self.power_controller.terminate_connection()
        self.scanner.stop_event.set()
        self.end_event.set()
        self.scanner.join()
        self.reconstructor.join()

    def get_image(self):
        try:
            image = -self.reconstructor.output_queue.get(timeout=0.001)
            if self.saver.saving_signal.is_set():
                if (
                    self.save_status is not None
                    and self.save_status.i_t + 1 == self.save_status.target_params.n_t
                ):
                    self.end_experiment()
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
        if not self.reference_event.is_set():
            self.saver.saving_parameter_queue.put(
                SavingParameters(
                    output_dir=Path(self.experiment_settings.save_dir),
                    plane_size=(self.scanning_parameters.n_x, self.scanning_parameters.n_y),
                    n_z=self.experiment_settings.n_planes,
                )
            )
        else:
            self.saver.saving_parameter_queue.put(
                SavingParameters(
                    output_dir=Path(self.experiment_settings.save_dir),
                    plane_size=(self.scanning_parameters.n_x, self.scanning_parameters.n_y),
                    n_z=(self.reference_params.extra_planes * 2) + self.experiment_settings.n_planes,
                )
            )

    def send_reference_params(self):
        param_to_send = convert_reference_params(self.reference_settings)
        if self.reference_event.is_set():
            n_planes = (self.reference_params.extra_planes * 2) + self.experiment_settings.n_planes
        else:
            n_planes = self.experiment_settings.n_planes
        param_to_send.n_planes = n_planes
        self.reference_params = param_to_send
        self.saver.reference_param_queue.put(param_to_send)

    def get_save_status(self) -> Optional[SavingStatus]:
        try:
            self.save_status = self.saver.saved_status_queue.get(timeout=0.001)
            return self.save_status
        except Empty:
            pass
        return None
