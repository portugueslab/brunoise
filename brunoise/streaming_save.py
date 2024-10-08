from multiprocessing import Process, Event, Queue
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from queue import Empty
import flammkuchen as fl
import numpy as np
import shutil
import json
import yagmail
from PIL import Image
import os
import time


@dataclass
class SavingParameters:
    output_dir: Path
    plane_size: tuple
    n_t: int = 100
    n_z: int = 1
    channel: str = "Green"
    notification_email: str = "None"
    notification_frequency: int = 3


@dataclass
class SavingStatus:
    target_params: SavingParameters
    i_t: int = 0
    i_z: int = 0


class StackSaver(Process):
    def __init__(self, stop_signal, data_queue, time_queue, n_frames_queue):
        super().__init__()
        self.stop_signal = stop_signal
        self.data_queue = data_queue
        self.time_queue = time_queue
        self.saving_signal = Event()
        self.n_frames_queue = n_frames_queue
        self.saving = False
        self.saving_parameter_queue = Queue()
        self.save_parameters: Optional[SavingParameters] = None
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = None
        self.saved_status_queue = Queue()
        self.dtype = np.int16
        # self.dtype = float
        self.current_time = None
        self.timestamps = None

    def run(self):
        while not self.stop_signal.is_set():
            if self.saving_signal.is_set() and self.save_parameters is not None:
                self.save_loop()
            else:
                self.receive_save_parameters()

    def save_loop(self):
        # remove files if some are found at the save location
        if (
                Path(self.save_parameters.output_dir) / "original" / "stack_metadata.json"
        ).is_file():
            shutil.rmtree(Path(self.save_parameters.output_dir) / "original")

        (Path(self.save_parameters.output_dir) / "original").mkdir(
            parents=True, exist_ok=True
        )
        if self.save_parameters.channel == "Both":
            (Path(self.save_parameters.output_dir) / "original" / "green").mkdir(
                parents=True, exist_ok=True
            )
            (Path(self.save_parameters.output_dir) / "original" / "red").mkdir(
                parents=True, exist_ok=True
            )

        i_received = 0
        self.i_in_plane = 0
        self.i_block = 0
        self.current_data = np.empty(
            (self.save_parameters.n_t, 2, *self.save_parameters.plane_size),
            dtype=self.dtype,
        )
        self.current_time = np.empty(self.save_parameters.n_t)
        n_total = self.save_parameters.n_t * self.save_parameters.n_z
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
        
        t_end = time.time()
        while time.time() - t_end < 5:
            try:
                frame = self.data_queue.get(timeout=0.01)
                self.fill_dataset(frame)
                break
            except Empty:
                pass
        
        if self.i_block > 0:
            self.finalize_dataset()
            if self.save_parameters.notification_email != "None":
                self.send_email_update(end=True)

        self.saving_signal.clear()
        self.save_parameters = None

    def cast(self, frame):
        """
        Conversion into a format appropriate for saving
        """
        if self.dtype == np.int16:
            frame = (frame / (2 / 2**12)).astype(self.dtype)
        return frame

    def update_n_t(self, n_t):
        if n_t != self.save_parameters.n_t:
            self.save_parameters.n_t = n_t
            old_data = self.current_data[: self.i_in_plane, :, :, :].copy()
            self.current_data = np.empty((n_t, *self.current_data.shape[1:]), dtype=self.dtype)
            self.current_data[: self.i_in_plane, :, :, :] = old_data
            old_time = self.current_time[: self.i_in_plane].copy()
            self.current_time = np.empty(n_t)
            self.current_time[: self.i_in_plane] = old_time

    def fill_dataset(self, frame):
        self.current_data[self.i_in_plane, :, :, :] = self.cast(frame)
        try:
            t = self.time_queue.get(timeout=0.001)
            self.current_time[self.i_in_plane] = t
        except Empty:
            print('time queue is empty')
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

    def dump_metadata(self, file):
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
            file,
        )

    def finalize_dataset(self):
        if self.save_parameters.channel == "Both":
            with open(
                    (
                            Path(self.save_parameters.output_dir)
                            / "original"
                            / "green"
                            / "stack_metadata.json"
                    ),
                    "w",
            ) as fg,\
            open(
                (
                        Path(self.save_parameters.output_dir)
                        / "original"
                        / "red"
                        / "stack_metadata.json"
                ),
                "w",
            ) as fr:
                self.dump_metadata(fg)
                self.dump_metadata(fr)
        else:
            with open(
                    (
                            Path(self.save_parameters.output_dir)
                            / "original"
                            / "stack_metadata.json"
                    ),
                    "w",
            ) as f:
                self.dump_metadata(f)

    def complete_plane(self):
        if self.i_block == 0:
            self.timestamps = self.current_time.copy() - self.current_time[0]
        else:
            self.timestamps = np.vstack((self.timestamps, self.current_time - self.current_time[0]))
        # save each time because the computer might crash before all planes are acquired
        fl.save(
            Path(self.save_parameters.output_dir)
            / "time.h5",
            self.timestamps.T,
            compression="blosc",
        )
        if self.save_parameters.channel == "Green":
            fl.save(
                Path(self.save_parameters.output_dir)
                / "original/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data[:,:1,:,:]},
                compression="blosc",
            )
        elif self.save_parameters.channel == "Red":
            fl.save(
                Path(self.save_parameters.output_dir)
                / "original/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data[:,1:,:,:]},
                compression="blosc",
            )
        else:
            fl.save(
                Path(self.save_parameters.output_dir)
                / "original/green/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data[:,:1,:,:]},
                compression="blosc",
            )
            fl.save(
                Path(self.save_parameters.output_dir)
                / "original/red/{:04d}.h5".format(self.i_block),
                {"stack_4D": self.current_data[:,1:,:,:]},
                compression="blosc",
            )
        self.i_block += 1

        if self.i_block % self.save_parameters.notification_frequency == 0 and \
                self.save_parameters.notification_email != "None":
            self.send_email_update(frame=self.current_data[self.i_in_plane - 1, 0, :, :])

        self.i_in_plane = 0

    def send_email_update(self, frame=None, end=False):
        sender_email = "fishgitbot@gmail.com"
        receiver_email = self.save_parameters.notification_email
        subject = "Progress update: Your 2P experiment"
        sender_password = "think_clear2020"
        if frame is not None:
            last_frame = Image.fromarray(frame, mode="L")
            #last_frame = last_frame.convert("RGB")
            last_frame.save("last_frame.png")

        yag = yagmail.SMTP(user=sender_email, password=sender_password)

        body = [
            "Hey!",
            "\n",
            "Update on your 2P experiment",
            "Plane #{} has just been acquired. See attached how this looks like".format(self.i_block),
            "\n"
            "Always yours,",
            "fishgitbot"
        ]

        if end:
            body = [
                "Hey!",
                "\n",
                "Your 2P experiment has finished! Come pick up your little fish",
                "\n"
                "Always yours,",
                "fishgitbot"
            ]

        if frame is not None:
            yag.send(
                to=receiver_email,
                subject=subject,
                contents=body,
                attachments=r"last_frame.png"
            )
        else:
            yag.send(
                to=receiver_email,
                subject=subject,
                contents=body,
            )

        try:
            os.remove(r"last_frame.png")
        except OSError:
            pass


    def receive_save_parameters(self):
        try:
            self.save_parameters = self.saving_parameter_queue.get(timeout=0.001)
        except Empty:
            pass
