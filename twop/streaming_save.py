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


@dataclass
class SavingStatus:
    target_params: SavingParameters
    i_t: int = 0
    i_z: int = 0


class StackSaver(Process):
    def __init__(self, stop_signal, data_queue, n_frames_queue):
        super().__init__()
        self.stop_signal = stop_signal
        self.data_queue = data_queue
        self.saving_signal = Event()
        self.n_frames_queue = n_frames_queue
        self.saving = False
        self.saving_parameter_queue = Queue()
        self.save_parameters: Optional[SavingParameters] = None
        self.i_in_plane = 0
        self.i_block = 0
        self.saving_dataset = None
        self.current_data = None
        self.saved_status_queue = Queue()

    def run(self):
        while not self.stop_signal.is_set():
            if self.saving_signal.is_set() and self.save_parameters is not None:
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
        print("Starting save loop")
        i_received = 0
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = np.empty(self.dataset.shape_block, dtype=np.float64)
        n_total = self.save_parameters.n_t * self.save_parameters.n_z
        while (
            i_received < n_total
            and self.saving_signal.is_set()
            and not self.stop_signal.is_set()
        ):
            try:
                self.save_parameters.n_t = self.n_frames_queue.get(timeout=0.001)
                n_total = self.save_parameters.n_t * self.save_parameters.n_z
            except Empty:
                pass
            try:
                frame = self.data_queue.get(timeout=0.01)
                self.fill_dataset(frame)
                i_received += 1
            except Empty:
                pass

        new_shape = (
            self.save_parameters.n_t,
            self.i_block,
            *self.save_parameters.plane_size,
        )
        self.dataset.shape_full = new_shape
        if self.i_block > 0:
            self.dataset.finalize()

        self.saving_signal.clear()
        self.save_parameters = None

    def cast(self, frame):
        """
        Conversion into a format appropriate for saving
        """
        return frame

    def fill_dataset(self, frame):
        self.current_data[self.i_in_plane, 0, :, :] = self.cast(frame)
        self.i_in_plane += 1
        self.saved_status_queue.put(
            SavingStatus(
                target_params=self.save_parameters,
                i_t=self.i_in_plane,
                i_z=self.i_block,
            )
        )
        if self.i_in_plane == self.save_parameters.n_t:
            self.complete_plane()

    def complete_plane(self):
        fl.save(
            Path(self.save_parameters.output_dir)
            / "original/{:04d}.h5".format(self.i_block),
            {"stack_4D": self.current_data},
            compression="blosc",
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
