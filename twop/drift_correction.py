from multiprocessing import Process
import numpy as np
from lightparam.param_qt import ParametrizedQt
from lightparam import Param


class ReferenceSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.name = "recording"
        self.n_frames = Param(10, (1, 500))
        self.n_planes = Param(5, (1, 500))
        self.dz = Param(1.0, (0.1, 20.0), unit="um")
        self.save_dir = Param(r"C:\Users\portugueslab\Desktop\test\python", gui=False)


class Corrector(Process):
    def __init__(self, reference_event, experiment_start_event, stop_event,
                 reference_queue, reference_param_queue, scanning_parameters_queue, data_queue,
                 motors, reference_settings):
        super().__init__()
        self.reference_event = reference_event
        self.experiment_start_event = experiment_start_event
        self.stop_event = stop_event

        self.reference_queue = reference_queue
        self.reference_param_queue = reference_param_queue
        self.scanning_parameters_queue = scanning_parameters_queue
        self.data_queue = data_queue
        self.reference_settings = reference_settings

        self.motors = motors
        self.x_pos = None
        self.y_pos = None
        self.z_pos = None

        self.from_plane = None
        self.to_plane = None

        self.actual_parameters = None
        self.reference = None
        self.eval_period = 5  # in seconds

    def run(self):
        while True:
            if self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.reference_loop()
                self.reference_event.clear()

            elif not self.reference_event.is_set() and self.experiment_start_event.is_set():
                self.exp_loop()

    def reference_loop(self):
        param_ref = self.reference_param_queue.get(timeout=0.001)   # empty the queue!
        param_scanning = self.scanning_parameters_queue(timeout=0.001)
        n_t = param_ref.target_params.n_t
        n_z = param_ref.target_params.n_z
        i_t = param_ref.i_t
        i_z = param_ref.i_z
        self.reference = np.empty((param_scanning.n_frames, param_ref.n_z, param_scanning.n_y,
                                   param_scanning.n_x + param_scanning.n_turn))
        while self.stop_event.is_set():
            if not n_t == i_t and not n_z == i_z:
                frame = self.reference_queue.get(timeout=0.001)
                print(frame)
                self.reference[i_t, i_z, :, :] = frame
            else:
                self.reference_processing()
                break

    def reference_processing(self):
        pass

    def compute_registration(self):
        pass

    def exp_loop(self):
        pass

    def start_acquisition(self):
        self.x_pos = self.motors["x"].get_position()
        self.y_pos = self.motors["y"].get_position()
        self.z_pos = self.motors["z"].get_position()
        if self.reference_settings.n_planes // 2:
            self.reference_settings.n_planes = self.reference_settings.n_planes + 1
        up_planes = (self.reference_settings.n_planes - 1) / 2
        distance = (self.reference_settings.dz / 1000) * up_planes
        self.motors["z"].more_rel = distance

    def end_acquisition(self):
        self.mototors["z"].move_abs(self.z_pos)
