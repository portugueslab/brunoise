from multiprocessing import Process, Queue
import numpy as np
from lightparam.param_qt import ParametrizedQt
from lightparam import Param
from skimage.feature import register_translation
from queue import Empty
from dataclasses import dataclass


class ReferenceSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "reference"
        self.n_frames_ref = Param(10, (1, 500))
        self.n_planes = Param(11, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0), unit="um")
        self.xy_th = Param(5.0, (0.1, 20.0), unit="um")
        dz = self.dz
        n_planes = self.n_planes
        max_z_th = dz * n_planes
        self.z_th = Param(self.dz, (self.dz, max_z_th), unit="um")
        self.n_frames_exp = Param(5, (1, 500))


@dataclass
class ReferenceParameters:
    n_frames_ref: int = 10
    n_planes: int = 11
    dz: float = 1.0
    xy_th: float = 5
    z_th: float = 1
    n_frames_exp: int = 5


def convert_reference_params(st: ReferenceSettings) -> ReferenceParameters:
    n_frames_ref = st.n_frames_ref
    n_planes = st.n_planes
    xy_th = st.xy_th
    dz = st.dz
    z_th = st.z_th
    n_frames_exp = st.n_frames_exp
    rp = ReferenceParameters(n_frames_ref=n_frames_ref,
                             n_planes=n_planes,
                             dz=dz,
                             xy_th=xy_th,
                             z_th=z_th,
                             n_frames_exp=n_frames_exp)

    return rp


class Corrector(Process):
    def __init__(self, reference_event, experiment_start_event, stop_event, correction_event,
                 reference_queue, reference_acq_param_queue, scanning_parameters_queue, data_queue,
                 input_commands_queues, output_positions_queues):
        super().__init__()
        self.reference_event = reference_event
        self.experiment_start_event = experiment_start_event
        self.stop_event = stop_event
        self.reference_params = None
        self.correction_event = correction_event

        self.reference_queue = reference_queue
        self.reference_acq_param_queue = reference_acq_param_queue
        self.reference_param_queue = Queue()
        self.scanning_parameters_queue = scanning_parameters_queue
        self.data_queue = data_queue
        self.input_commands_queues = input_commands_queues
        self.output_positions_queues = output_positions_queues

        self.x_pos = None
        self.y_pos = None
        self.z_pos = None

        self.from_plane = None
        self.to_plane = None

        self.actual_parameters = None
        self.reference = None
        self.eval_period = 5  # in seconds
        self.calibration_vector = None

    def run(self):
        while True:
            if self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.reference_loop()
                self.reference_event.clear()

            elif not self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.correction_event.set()
                self.exp_loop()
                self.correction_event.clear()

    def reference_loop(self):
        param_acq_ref = self.get_last_entry(self.reference_acq_param_queue)
        param_scanning = self.get_last_entry(self.scanning_parameters_queue)
        n_t = param_acq_ref.target_params.n_t
        n_z = param_acq_ref.target_params.n_z
        ref = np.empty((param_scanning.n_frames, param_acq_ref.n_z, param_scanning.n_y,
                        param_scanning.n_x + param_scanning.n_turn))
        while self.stop_event.is_set():
            param_acq_ref = self.get_last_entry(self.reference_acq_param_queue)  # or normal call?
            if not n_t == param_acq_ref.i_t and not n_z == param_acq_ref.i_z:
                frame = self.reference_queue.get(timeout=0.001)
                print(frame)
                ref[param_acq_ref.i_t, param_acq_ref.i_z, :, :] = frame
            else:
                self.reference = self.reference_processing(ref)
                self.end_ref_acquisition()

    def compute_registration(self, test_image):
        vectors = []
        errors = []
        planes = np.size(self.reference, 0)
        for i in range(planes):
            ref_im = np.squeeze(self.reference[i, :, :])
            output = register_translation(ref_im, test_image)
            vectors.append(output[0])
            errors.append(output[1])
        ind = errors.index(min(errors))
        z_disp = ind - ((self.reference_settings.n_planes - 1) / 2)
        vector = vectors[ind]
        np.append(vector, z_disp)
        vector = self.real_units(vector)
        return vector

    def exp_loop(self):
        self.calibration_vector = [0, 0, self.reference_settings.dz.value / 1000]
        while not self.stop_event.is_set():
            number_of_frames = 0
            frame_container = []
            while number_of_frames == self.reference_settings.n_frames_exp:
                try:
                    frame = self.data_queue.get(timeout=0.001)
                    frame_container.append(frame)
                    number_of_frames += 1
                except Empty:
                    frame_container = frame_container[-self.reference_settings.n_frames_exp:]
                frame = self.frame_processing(frame_container)
                vector = self.compute_registration(frame)
                self.apply_correction(vector)

    def start_ref_acquisition(self):
        self.x_pos = self.get_last_entry(self.output_positions_queues["x"])
        self.y_pos = self.get_last_entry(self.output_positions_queues["y"])
        self.z_pos = self.get_last_entry(self.output_positions_queues["z"])
        if self.reference_params.n_planes // 2:
            self.reference_params.n_planes = self.reference_params.n_planes + 1
        up_planes = (self.reference_params.n_planes - 1) / 2
        distance = (self.reference_params.dz / 1000) * up_planes
        self.input_commands_queues["z"].put((distance, False))

    def end_ref_acquisition(self):
        self.input_commands_queues["z"].put((self.z_pos, True))

    def real_units(self, raw_vector):
        vector = np.multiply(raw_vector, self.calibration_vector)
        return vector

    def apply_correction(self, vector):
        self.input_commands_queues["x"].put((vector[1], False))
        self.input_commands_queues["y"].put((vector[0], False))
        self.input_commands_queues["z"].put((vector[2], False))

    @staticmethod
    def reference_processing(input_ref):
        output_ref = np.mean(input_ref, axis=0)
        return output_ref

    @staticmethod
    def frame_processing(frame_container):
        frame_container_array = np.array(frame_container)
        frame = np.mean(frame_container_array, 0)
        return frame

    @staticmethod
    def get_last_entry(queue):
        while True:
            try:
                out = queue.get(timeout=0.001)
            except Empty:
                break
        return out

    def update_settings(self):
        self.reference_params = self.get_last_entry(self.reference_param_queue)