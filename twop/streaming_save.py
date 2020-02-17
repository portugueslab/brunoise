from multiprocessing import Process, Event, Queue
from dataclasses import dataclass
from fimpy.core.split_dataset import EmptyH5Dataset
from pathlib import Path
from typing import Optional
from queue import Empty
import flammkuchen as fl
import numpy as np


@dataclass
class SavingParameters:
    output_dir: Path
    plane_size: tuple
    n_t: int = 100
    n_z: int = 1


class StackSaver(Process):
    def __init__(self, data_queue, stop_signal: Event, n_frames_queue):
        super().__init__()
        self.data_queue = data_queue
        self.stop_signal = stop_signal
        self.start_saving = Event()
        self.stop_saving = Event()
        self.n_frames_queue = n_frames_queue
        self.saving = False
        self.saving_parameter_queue = Queue()
        self.save_parameters: Optional[SavingParameters] = None
        self.i_in_plane = 0
        self.i_block = 0
        self.saving_dataset = None
        self.current_data = None

    def run(self):
        while not self.stop_signal.is_set():
            if self.start_saving.is_set():
                self.save_loop()
            else:
                self.receive_save_parameters()

    def save_loop(self):
        self.dataset = EmptyH5Dataset(
            root=self.save_parameters.output_dir,
            name="original",
            shape_block=(self.save_parameters.n_t, 1, *self.save_parameters.plane_size),
            shape_full=(
                self.save_parameters.n_t,
                self.save_parameters.n_z,
                *self.save_parameters.plane_size,
            ),
        )
        i_received = 0
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = np.empty(self.dataset.shape_block, dtype=np.float64)
        n_total = self.save_parameters.n_t * self.save_parameters.n_z
        while i_received < n_total and not self.stop_signal.is_set():
            try:
                self.save_parameters.n_t = self.n_frames_queue.get(timeout=0.001)
                n_total = self.save_parameters.n_t * self.save_parameters.n_z
            except:
                pass
            try:
                frame = self.data_queue.get(timeout=0.01)
                self.fill_dataset(frame)
                i_received += 1
            except Empty:
                pass
        self.dataset.shape_full = (
            (
                self.save_parameters.n_t,
                self.i_block,
                *self.save_parameters.plane_size,
            ),
        )
        self.dataset.finalize()
        self.start_saving.clear()
        self.stop_signal.clear()
        self.save_parameters = None

    def cast(self, frame):
        """
        Conversion into a format appropriate for saving
        """
        return frame

    def fill_dataset(self, frame):
        self.current_data[self.i_in_plane, 0, :, :] = self.cast(frame)
        self.i_in_plane += 1
        if self.i_in_plane == self.save_parameters.n_t:
            self.complete_plane()

    def complete_plane(self):
        print("Completing plane")
        fl.save(
            Path(self.save_parameters.output_dir)
            / "original/{:04d}.h5".format(self.i_block),
            {"stack_4D": self.current_data},
        )
        self.i_in_plane = 0
        self.i_block += 1
        self.dataset.shape_full = (
            self.save_parameters.n_t,
            self.i_block,
            *self.dataset.shape_full[:2],
        )

    def receive_save_parameters(self):
        try:
            self.save_parameters = self.saving_parameter_queue.get(timeout=0.001)
        except Empty:
            pass
