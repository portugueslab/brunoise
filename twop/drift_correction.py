from multiprocessing import Process, Queue
import numpy as np
from lightparam.param_qt import ParametrizedQt
from lightparam import Param
from skimage.feature import register_translation
import flammkuchen as fl
from matplotlib import Path
from queue import Empty
from dataclasses import dataclass
from time import sleep
from scipy.ndimage.filters import gaussian_filter
from twop.objective_motor_sliders import MovementType
from scipy.signal import convolve
from twop.objective_motor_sliders import get_next_entry
import json
class ReferenceSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "reference"
        self.n_frames_ref = Param(10, (1, 500))
        self.extra_planes = Param(11, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0), unit="um")
        self.xy_th = Param(5.0, (0.1, 20.0), unit="um")
        self.z_th = Param(self.dz, (self.dz, self.dz * 4), unit="um")
        self.n_frames_exp = Param(5, (1, 500))
        self.blur_kernel = Param(5, (0, 100))



@dataclass
class ReferenceParameters:
    extra_planes: int = 10
    xy_th: float = 5
    z_th: float = 1
    n_frames_exp: int = 5


def convert_reference_params(st: ReferenceSettings) -> ReferenceParameters:
    extra_planes = st.extra_planes
    xy_th = st.xy_th
    z_th = st.z_th
    n_frames_exp = st.n_frames_exp
    rp = ReferenceParameters(
                             extra_planes=extra_planes,
                             xy_th=xy_th,
                             z_th=z_th,
                             n_frames_exp=n_frames_exp
                             )

    return rp


class Corrector(Process):
    def __init__(self, reference_event, experiment_start_event, stop_event, correction_pre_event, correction_event,
                 reference_queue, scanning_parameters,
                 scanning_parameters_queue, data_queue,
                 input_commands_queues, output_positions_queues, save_param_queue_drift):
        super().__init__()
        # communication with other processes, active during acquisition of the reference
        self.reference_event = reference_event
        # communication with other processes, active during acquisition of the reference and experiment
        # (all the processes use it)
        self.experiment_start_event = experiment_start_event
        # communication with other processes, the status is not modified by any process
        self.stop_event = stop_event
        # communication with other processes, active during experiment (when correction is allowed)
        self.correction_pre_event = correction_pre_event

        self.correction_event = correction_event

        # queue for the acquisition of the reference, planes are sent by the saver
        self.reference_queue = reference_queue
        # queue in order to know the latest settings selected by the user such as n_planes, n_frames etc.
        self.reference_param_queue = Queue()
        # queue in order to know the latest scanning settings, for n_x and n_y
        self.scanning_parameters_queue = scanning_parameters_queue
        # initial scanning parameters
        self.scanning_parameters = scanning_parameters
        # queue for getting the copy of the frames during an experiment
        self.data_queue = data_queue
        # queue for the communication with the master motor class (in a separate process), this is for move the motors
        self.input_commands_queues = input_commands_queues
        # queue for the communication with the master motor class (in a separate process),
        # this is for read the last position
        self.output_positions_queues = output_positions_queues
        # to know the directory where the anatomy/reference will be saved
        self.save_parameters_queue_drift = save_param_queue_drift
        self.save_parameters = None

        self.x_pos = None
        self.y_pos = None
        self.z_pos = None
        self.mov_type = MovementType(False)
        self.desired_plane = None

        self.reference = None
        self.reference_params = None
        self.reference_acq_params = None
        self.calibration_vector = None
        self.corrected_exp = False

    def run(self):
        while True:
            self.update_settings()
            self.receive_save_parameters()
            if self.correction_pre_event.is_set():
                self.load_reference()
                self.correction_pre_event.clear()
                self.correction_event.set()
            if self.correction_event.is_set():
                self.exp_loop()

    def compute_registration(self, test_image):
        vectors = []
        errors = []
        planes = np.size(self.reference, 0)
        for i in range(planes):
            ref_im = self.reference[i, :, :]
            output = register_translation(ref_im, test_image)
            vectors.append(output[0])
            errors.append(output[1])
        ind = errors.index(min(errors))
        z_disp = ind - ((self.reference_params.n_planes - 1) / 2)
        vector = vectors[ind]
        np.append(vector, z_disp)
        vector = self.real_units(vector)
        return vector

    def exp_loop(self):
        pix_millimeter = self.calculate_fov()
        self.calibration_vector = [pix_millimeter, pix_millimeter, self.reference_acq_params["dz"]]  # x,y,z cal vect
        while not self.stop_event.is_set() or self.correction_event.is_set():
            number_of_frames = 0
            frame_container = []
            while number_of_frames == self.reference_params.n_frames_exp:
                try:
                    frame = self.data_queue.get(timeout=0.001)
                    frame_container.append(frame)
                    number_of_frames += 1
                except Empty:
                    frame_container = frame_container[-self.reference_params.n_frames_exp:]
                frame = self.frame_processing(frame_container)
                vector = self.compute_registration(frame)
                self.apply_correction(vector)

    def real_units(self, raw_vector):
        vector = np.multiply(raw_vector, self.calibration_vector)
        return vector

    def apply_correction(self, vector):
        print("x corrected by", vector[1])
        print("y corrected by", vector[0])
        print("z corrected by", vector[2])
        # self.input_commands_queues["x"].put((vector[1], self.mov_type))
        # self.input_commands_queues["y"].put((vector[0], self.mov_type))
        # self.input_commands_queues["z"].put((vector[2], self.mov_type))

    # def reference_processing(self, input_ref):
    #     return gaussian_filter(input_ref, self.reference_params.size_k, mode='same')

    @staticmethod
    def frame_processing(frame_container):
        frame_container_array = np.array(frame_container)
        frame = np.mean(frame_container_array, 0)
        return frame

    @staticmethod
    def get_last_entry(queue):
        out = None
        while True:
            try:
                out = queue.get(timeout=0.001)
            except Empty:
                break
        return out

    def update_settings(self):
        new_params = self.get_last_entry(self.scanning_parameters_queue)
        if new_params is not None:
            self.scanning_parameters = new_params

    def calculate_fov(self):
        # calculate pix per millimeters
        # formula: width FOV (microns) = 167.789 * Voltage
        conv_fact = 167.789
        w_fov = conv_fact * self.scanning_parameters.voltage_x
        return (self.scanning_parameters.n_x / w_fov) / 1000

    def load_reference(self):
        ref_path = Path(self.save_parameters.output_dir / "anatomy")
        meta_files = sorted(ref_path.glob("*metadata*"))

        with open(str(meta_files[0])) as json_file:
            self.reference_acq_params = json.load(json_file)
        ref_files = sorted(ref_path.glob("*.h5"))
        raw_reference = np.zeros((len(ref_files),
                                self.reference_acq_params["shape_full"][2],
                                self.reference_acq_params["shape_full"][3]))
        for n, plane_file in enumerate(ref_files):
            raw_reference[n, :, :] = fl.load(str(plane_file))["plane"]
        # self.reference = self.reference_processing(raw_reference)
        self.reference = raw_reference
        print("ref shape", raw_reference.shape)
        self.desired_plane = self.reference_acq_params["extra_planes"]
        self.correction_event.set()

    def receive_save_parameters(self):
        try:
            self.save_parameters = self.save_parameters_queue_drift.get(timeout=0.001)
        except Empty:
            pass