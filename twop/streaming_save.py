from multiprocessing import Process, Event, Queue
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from queue import Empty
import flammkuchen as fl
import numpy as np
import shutil
import json


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
    def __init__(self, stop_signal, data_queue, n_frames_queue, ref_event, ref_queue):
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
        self.current_data = None
        self.reference = None
        self.saved_status_queue = Queue()
        self.dtype = np.float32
        self.ref_event = ref_event
        self.ref_queue = ref_queue
        self.reference_param_queue = Queue()

    def run(self):
        while not self.stop_signal.is_set():
            if self.saving_signal.is_set() and self.save_parameters is not None:
                self.save_loop()
            else:
                self.receive_save_parameters()

    def save_loop(self):
        # remove files if some are found at the save location
        if not self.ref_event.is_set():
            if (
                Path(self.save_parameters.output_dir) / "original" / "stack_metadata.json"
            ).is_file():
                shutil.rmtree(Path(self.save_parameters.output_dir) / "original")

            (Path(self.save_parameters.output_dir) / "original").mkdir(
                parents=True, exist_ok=True
            )
        else:
            if (
                    Path(self.save_parameters.output_dir) / "anatomy" / "stack_metadata.json"
            ).is_file():
                shutil.rmtree(Path(self.save_parameters.output_dir) / "anatomy")

            (Path(self.save_parameters.output_dir) / "anatomy").mkdir(
                parents=True, exist_ok=True
            )
            # corrected_n_planes = (self.reference_param_queue.get(timeout=0.001)).n_planes
            # self.save_parameters.n_z = corrected_n_planes
            print("new n planes", self.save_parameters.n_z)

        i_received = 0
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = np.empty(
            (self.save_parameters.n_t, 1, *self.save_parameters.plane_size),
            dtype=self.dtype,
        )
        n_total = self.save_parameters.n_t * self.save_parameters.n_z
        print("total number of frames", self.save_parameters.n_z)
        while (
            i_received < n_total
            and self.saving_signal.is_set()
            and not self.stop_signal.is_set()
        ):
            self.receive_save_parameters()
            try:
                self.update_n_t(self.n_frames_queue.get(timeout=0.001))
                n_total = self.save_parameters.n_t * self.save_parameters.n_z
            except Empty:
                pass
            try:
                frame = self.data_queue.get(timeout=0.01)
                self.fill_dataset(frame)
                i_received += 1
            except Empty:
                pass

        if self.i_block > 0:
            self.finalize_dataset()

        self.saving_signal.clear()
        self.save_parameters = None

    def cast(self, frame):
        """
        Conversion into a format appropriate for saving
        """
        return frame

    def update_n_t(self, n_t):
        if n_t != self.save_parameters.n_t:
            self.save_parameters.n_t = n_t
            old_data = self.current_data[: self.i_in_plane, :, :, :].copy()
            self.current_data = np.empty((n_t, *self.current_data.shape[1:]))
            self.current_data[: self.i_in_plane, :, :, :] = old_data

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

    def finalize_dataset(self):
        with open(
            (
                Path(self.save_parameters.output_dir)
                / "original"
                / "stack_metadata.json"
            ),
            "w",
        ) as f:
            json.dump(
                {
                    "shape_full": (
                        self.save_parameters.n_t,
                        self.i_block,
                        *self.current_data.shape[2:],
                    ),
                    "shape_block": (
                        self.save_parameters.n_t,
                        1,
                        *self.current_data.shape[2:],
                    ),
                    "crop_start": [0, 0, 0, 0],
                    "crop_end": [0, 0, 0, 0],
                    "padding": [0, 0, 0, 0],
                },
                f,
            )

    def complete_plane(self):
        if not self.ref_event.is_set():
            fl.save(
                Path(self.save_parameters.output_dir)
                / "original/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data},
                compression="blosc",
            )
        else:
            fl.save(
                Path(self.save_parameters.output_dir)
                / "anatomy/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data},
                compression="blosc",
            )
            self.fill_reference()
        self.i_in_plane = 0
        self.i_block += 1

    def receive_save_parameters(self):
        try:
            self.save_parameters = self.saving_parameter_queue.get(timeout=0.001)
        except Empty:
            pass

    def fill_reference(self):
        if self.i_block == 0:
            self.reference = np.zeros((
                int(self.save_parameters.n_t),
                int(self.save_parameters.n_z),
                self.current_data.shape[2],
                self.current_data.shape[3]))
        self.reference[:, self.i_block, :, :] = self.current_data[:, 0, :, :]
        if self.i_block == self.save_parameters.n_z - 1:
            self.send_reference()

    def send_reference(self):
        self.ref_queue.put(self.reference)
