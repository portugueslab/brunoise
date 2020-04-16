from multiprocessing import Process, Queue
import numpy as np
from lightparam.param_qt import ParametrizedQt
from lightparam import Param
from skimage.feature import register_translation
from queue import Empty
from dataclasses import dataclass
from time import sleep
from scipy.ndimage.filters import gaussian_filter
from scipy.signal import convolve


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
        self.size_k = Param(0, (0, 100))
        self.sigma_k = Param(2, (1, 10))



@dataclass
class ReferenceParameters:
    n_frames_ref: int = 10
    extra_planes: int = 10
    dz: float = 1.0
    xy_th: float = 5
    z_th: float = 1
    n_frames_exp: int = 5
    size_k: int = 0
    sigma_k: int = 5


def convert_reference_params(st: ReferenceSettings) -> ReferenceParameters:
    n_frames_ref = st.n_frames_ref
    extra_planes = st.extra_planes
    xy_th = st.xy_th
    dz = st.dz
    z_th = st.z_th
    n_frames_exp = st.n_frames_exp
    sigma_k = st.sigma_k
    size_k = st.size_k
    rp = ReferenceParameters(n_frames_ref=n_frames_ref,
                             extra_planes=extra_planes,
                             dz=dz,
                             xy_th=xy_th,
                             z_th=z_th,
                             n_frames_exp=n_frames_exp,
                             sigma_k=sigma_k,
                             size_k=size_k)

    return rp


class Corrector(Process):
    def __init__(self, reference_event, experiment_start_event, stop_event, correction_event,
                 reference_queue, scanning_parameters,
                 scanning_parameters_queue, data_queue,
                 input_commands_queues, output_positions_queues):
        super().__init__()
        # communication with other processes, active during acquisition of the reference
        self.reference_event = reference_event
        # communication with other processes, active during acquisition of the reference and experiment
        # (all the processes use it)
        self.experiment_start_event = experiment_start_event
        # communication with other processes, the status is not modified by any process
        self.stop_event = stop_event
        # communication with other processes, active during experiment (when correction is allowed)
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
        # queue for the communication with the master motor class (in a separate process), this is for read the last position
        self.output_positions_queues = output_positions_queues

        self.x_pos = None
        self.y_pos = None
        self.z_pos = None

        self.reference = None
        self.calibration_vector = None
        self.reference_params = None

    def run(self):
        while True:
            self.update_settings()
            if self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.start_ref_acquisition()
                self.reference_loop()
                self.reference_event.clear()

            elif not self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.correction_event.set()
                self.exp_loop()
                self.correction_event.clear()

    def reference_loop(self):
        stack_4d = self.get_next_entry(self.reference_queue)
        print(stack_4d)
        self.reference = self.reference_processing(stack_4d)
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
        z_disp = ind - ((self.reference_params.n_planes - 1) / 2)
        vector = vectors[ind]
        np.append(vector, z_disp)
        vector = self.real_units(vector)
        return vector

    def exp_loop(self):
        self.calibration_vector = [0, 0, self.reference_params.dz.value / 1000]
        while not self.stop_event.is_set():
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

    def start_ref_acquisition(self):
        print(self.reference_params.n_planes)
        self.x_pos = self.get_last_entry(self.output_positions_queues["x"])
        self.y_pos = self.get_last_entry(self.output_positions_queues["y"])
        self.z_pos = self.get_last_entry(self.output_positions_queues["z"])
        print(self.x_pos, self.y_pos, self.z_pos)
        # self.reference_params.n_planes = self.reference_params.n_planes + 1
        up_planes = self.reference_params.extra_planes
        distance = (self.reference_params.dz / 1000) * up_planes
        self.input_commands_queues["z"].put((distance, False))
        sleep(0.2)

    def end_ref_acquisition(self):
        self.input_commands_queues["z"].put((self.z_pos, True))

    def real_units(self, raw_vector):
        vector = np.multiply(raw_vector, self.calibration_vector)
        return vector

    def apply_correction(self, vector):
        self.input_commands_queues["x"].put((vector[1], False))
        self.input_commands_queues["y"].put((vector[0], False))
        self.input_commands_queues["z"].put((vector[2], False))

    def reference_processing(self, input_ref):
        print(input_ref.shape)
        output_ref = np.mean(input_ref, axis=0)
        size_kernel = self.reference_params.size_k
        sigma = self.reference_params.sigma_k
        if size_kernel != 0:
            kernel = self.gaussian_kernel((size_kernel,)*3, sigma=sigma)
            output_ref = convolve(output_ref, kernel, mode='same')
        return output_ref

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

    @staticmethod
    def get_next_entry(queue):
        out = None
        while out is not None:
            try:
                out = queue.get(timeout=0.001)
            except Empty:
                break
        return out

    @staticmethod
    def gaussian_kernel(size_kernel, sigma=1):
        size_kernel = np.ceil(size_kernel) // 2 * 2 + 1
        x = np.arange(- np.floor(size_kernel[0] / 2), np.ceil(size_kernel[0] / 2), 1)
        y = np.arange(- np.floor(size_kernel[1] / 2), np.ceil(size_kernel[1] / 2), 1)
        if len(size_kernel) == 3:
            z = np.arange(- np.floor(size_kernel[2] / 2), np.ceil(size_kernel[2] / 2), 1)
            xx, yy, zz = np.meshgrid(x, y, z)
            kernel = np.exp(-(xx ** 2 + yy ** 2 + zz ** 2) / (2 * sigma ** 2))
        else:
            xx, yy = np.meshgrid(x, y)
            kernel = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
        return kernel

    def update_settings(self):
        new_params = self.get_last_entry(self.reference_param_queue)
        if new_params is not None:
            self.reference_params = new_params
        new_params = self.get_last_entry(self.scanning_parameters_queue)
        if new_params is not None:
            self.scanning_parameters = new_params
