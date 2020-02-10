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
    n_t: int
    n_z: int


class StackSaver(Process):
    def __init__(self, data_queue, stop_signal: Event):
        super().__init__()
        self.data_queue = data_queue
        self.stop_signal = stop_signal
        self.stop_saving = Event()
        self.saving = False
        self.saving_parameter_queue = Queue()
        self.save_parameters: Optional[SavingParameters] = None
        self.i_in_plane = 0
        self.i_block = 0
        self.saving_dataset = None
        self.current_data = None

    def run(self):
        while not self.stop_signal.is_set():
            if self.saving:
                self.save_loop()
            else:
                self.receive_save_parameters()

    def save_loop(self):
        self.dataset = EmptyH5Dataset(
            root=self.save_parameters.ouput_dir,
            name="original",
            shape_block=(*self.save_parameters.plane_size, 1, self.save_parameters.n_t),
            shape_full=(
                *self.save_parameters.plane_size,
                self.save_parameters.n_z,
                self.save_parameters.n_t,
            ),
        )
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = np.empty(self.dataset.shape_block, dtype=np.uint16)
        while self.i_received < self.save_parameters and not self.stop_signal.is_set():
            try:
                frame = self.data_queue.get(timeout=0.01)
                self.fill_dataset(frame)
                if self.i_in_plane == self.save_parameters.n_t - 1:
                    self.complete_plane()

            except Empty:
                pass
        if self.stop_signal.is_set():
            # TODO make the output dataset valid by discarding the unfinished plane and
            # completing the dataset
            pass
        self.dataset.finalize()
        self.saving = False
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

    def complete_plane(self):
        fl.save(
            self.save_parameters.output_dir / "{:04d}.h5".format(self.i_block),
            {"stack_4D": self.current_data},
        )
        self.i_in_plane = 0
        self.i_block += 1
        self.dataset.shape_full = (
            *self.dataset.shape_full[:2],
            self.i_block,
            self.save_parameters.n_t,
        )

    def receive_save_parameters(self):
        self.save_parameters = self.saving_parameter_queue.get(timeout=0.001)
        if self.save_parameters is not None:
            self.saving = True
            self.i_received = 0
