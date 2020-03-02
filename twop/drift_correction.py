from multiprocessing import Process
import numpy as np


class Corrector(Process):
    def __init__(self, reference_event, experiment_start_event, stop_signal,
                 reference_queue, reference_param_queue, scanning_parameters_queue, data_queue,
                 motors):
        super().__init__()
        self.reference_event = reference_event
        self.experiment_start_event = experiment_start_event
        self.stop_signal = stop_signal

        self.reference_queue = reference_queue
        self.reference_param_queue = reference_param_queue
        self.scanning_parameters_queue = scanning_parameters_queue
        self.data_queue = data_queue

        self.motor_x = motors["x"]
        self.motor_y = motors["y"]
        self.motor_z = motors["z"]

        self.actual_parameters = None
        self.reference = None
        self.eval_period = 5 #in seconds

    def main_loop(self):
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
        self.reference = np.empty(())
        while n_t == i_t and n_z == i_z:
            frame = self.reference_queue.get(timeout=0.001)

    def compute_registration(self):
        pass

    def exp_loop(self):
        pass
