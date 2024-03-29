from multiprocessing import Event, Process, Queue
import numpy as np
try:
    import nidaqmx
    from nidaqmx import Task
    from nidaqmx.stream_readers import AnalogMultiChannelReader
    from nidaqmx.stream_writers import AnalogMultiChannelWriter
    from nidaqmx.constants import Edge, AcquisitionType, LineGrouping
except ImportError:
    from theknights.task import Task
    from theknights.stream_readers import AnalogMultiChannelReader
    from theknights.stream_writers import AnalogMultiChannelWriter
    from theknights.constants import Edge, AcquisitionType, LineGrouping


from arrayqueues.shared_arrays import ArrayQueue
from queue import Empty

import scanning_patterns
from copy import copy
from dataclasses import dataclass
from enum import Enum
from time import sleep, perf_counter
from math import ceil


class ScanningState(Enum):
    PREVIEW = 1
    EXPERIMENT_RUNNING = 2
    PAUSED = 3


@dataclass
class ScanningParameters:
    n_x: int = 400
    n_y: int = 400
    voltage_x: float = 3
    voltage_y: float = 3
    n_bin: int = 10
    n_turn: int = 10
    n_extra: int = 10
    mystery_offset: int = -400
    sample_rate_out: float = 500000.0
    scanning_state: ScanningState = ScanningState.PREVIEW
    shutter: bool = False
    n_frames: int = 100
    framerate: int = 2
    pause: bool = True


@dataclass
class RoiParameters:
    roi_scanning: bool = False
    roi_write_signals: object = np.empty(0)


def frame_duration(sp: ScanningParameters):
    return (
        scanning_patterns.n_total(sp.n_x, sp.n_y, sp.n_turn, sp.n_extra, sp.pause)
        / sp.sample_rate_out
    )


def compute_waveform(sp: ScanningParameters):
    return scanning_patterns.simple_scanning_pattern(
        sp.n_x, sp.n_y, sp.n_turn, sp.n_extra, sp.pause
    )


class Scanner(Process):
    def __init__(self, experiment_start_event, duration_queue, max_queuesize=200):
        super().__init__()
        self.data_queue = ArrayQueue(max_mbytes=max_queuesize)
        self.time_queue = Queue()
        self.parameter_queue = Queue()
        self.roi_queue = Queue()
        self.stop_event = Event()
        self.experiment_start_event = experiment_start_event
        self.scanning_parameters = ScanningParameters()
        self.new_parameters = copy(self.scanning_parameters)
        self.roi_parameters = RoiParameters()
        self.new_roi_parameters = copy(self.roi_parameters)
        self.duration_queue = duration_queue
        self.n_frames_queue = Queue()

    def run(self):
        self.compute_scan_parameters()
        self.run_scanning()

    def compute_scan_parameters(self):
        self.extent_x = (
            -self.scanning_parameters.voltage_x,
            self.scanning_parameters.voltage_x,
        )
        self.extent_y = (
            -self.scanning_parameters.voltage_y,
            self.scanning_parameters.voltage_y,
        )

        self.n_x = self.scanning_parameters.n_x
        self.n_y = self.scanning_parameters.n_y
        self.raw_x, self.raw_y = compute_waveform(self.scanning_parameters)
        self.pos_x = (
            self.raw_x * ((self.extent_x[1] - self.extent_x[0]) / self.n_x)
            + self.extent_x[0]
        )
        self.pos_y = (
            self.raw_y * ((self.extent_y[1] - self.extent_y[0]) / self.n_y)
            + self.extent_y[0]
        )

        self.n_bin = self.scanning_parameters.n_bin

        self.n_samples_out = len(self.raw_x)
        self.n_samples_in = self.n_samples_out * self.n_bin

        self.sample_rate_out = self.scanning_parameters.sample_rate_out
        self.plane_duration = self.n_samples_out / self.sample_rate_out

        self.sample_rate_in = self.n_bin * self.sample_rate_out

        self.write_signals = np.stack([self.pos_x, self.pos_y], 0)
        self.read_buffer = np.zeros((4, self.n_samples_in))
        self.mystery_offset = self.scanning_parameters.mystery_offset

        self.roi_scanning = self.roi_parameters.roi_scanning
        self.roi_write_signals = np.ascontiguousarray(self.roi_parameters.roi_write_signals)

    def setup_tasks(self, read_task, write_task, shutter_task):
        # Configure the channels
        read_task.ai_channels.add_ai_voltage_chan(
            "Dev1/ai0:3", min_val=-1, max_val=1
        )  # channels are 0: green PMT, 1 x galvo pos 2 y galvo pos, 3 red PMT
        write_task.ao_channels.add_ao_voltage_chan(
            "Dev1/ao0:1", min_val=-10, max_val=10
        )
        shutter_task.do_channels.add_do_chan(
            "Dev1/port0/line1", line_grouping=LineGrouping.CHAN_PER_LINE
        )
        # Set the timing of both to the onboard clock so that they are synchronised
        read_task.timing.cfg_samp_clk_timing(
            rate=self.sample_rate_in,
            source="OnboardClock",
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=self.n_samples_in,
        )
        write_task.timing.cfg_samp_clk_timing(
            rate=self.sample_rate_out,
            source="OnboardClock",
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=self.n_samples_out,
        )

        # This is necessary to synchronise reading and wrting
        read_task.triggers.start_trigger.cfg_dig_edge_start_trig(
            "/Dev1/ao/StartTrigger", Edge.RISING
        )

    def check_start_plane(self):
        if self.scanning_parameters.scanning_state == ScanningState.EXPERIMENT_RUNNING:
            while not self.experiment_start_event.is_set():
                sleep(0.00001)

    def calculate_duration(self):
        try:
            duration = self.duration_queue.get(timeout=0.0001)
            self.scanning_parameters.n_frames = (
                int(ceil(duration / frame_duration(self.scanning_parameters))) + 1
            )
            self.n_frames_queue.put(self.scanning_parameters.n_frames)
        except Empty:
            pass

    def scan_loop(self, read_task, write_task):
        writer = AnalogMultiChannelWriter(write_task.out_stream)
        reader = AnalogMultiChannelReader(read_task.in_stream)

        first_write = True
        i_acquired = 0
        while not self.stop_event.is_set() and (
            not self.scanning_parameters.scanning_state
            == ScanningState.EXPERIMENT_RUNNING
            or i_acquired < self.scanning_parameters.n_frames
        ):
            # The first write has to be defined before the task starts
            try:
                if self.roi_scanning and len(self.roi_write_signals) == 2:
                    writer.write_many_sample(self.roi_write_signals)
                else:
                    writer.write_many_sample(self.write_signals)
                if i_acquired == 0:
                    self.check_start_plane()
                if first_write:
                    read_task.start()
                    write_task.start()
                    first_write = False
                reader.read_many_sample(
                    self.read_buffer,
                    number_of_samples_per_channel=self.n_samples_in,
                    timeout=1,
                )
                self.time_queue.put(perf_counter())
                i_acquired += 1
            except nidaqmx.DaqError as e:
                print(e)
                break
            self.data_queue.put(np.stack([self.read_buffer[0, :], self.read_buffer[-1, :]]))
            # if new parameters have been received and changed, update
            # them, breaking out of the loop if the experiment is not running
            try:
                self.new_parameters = self.parameter_queue.get(timeout=0.0001)
                if self.new_parameters != self.scanning_parameters and (
                    self.scanning_parameters.scanning_state
                    != ScanningState.EXPERIMENT_RUNNING
                    or self.new_parameters.scanning_state == ScanningState.PREVIEW
                ):
                    break
            except Empty:
                pass
            try:
                self.new_roi_parameters = self.roi_queue.get(timeout=0.0001)
                if self.new_roi_parameters.roi_scanning != self.roi_parameters.roi_scanning:
                    break
            except Empty:
                pass

            # calculate duration
            self.calculate_duration()

    def pause_loop(self):
        while not self.stop_event.is_set():
            try:
                self.new_parameters = self.parameter_queue.get(timeout=0.001)
                if self.new_parameters != self.scanning_parameters and (
                    self.scanning_parameters.scanning_state
                    != ScanningState.EXPERIMENT_RUNNING
                    or self.new_parameters.scanning_state == ScanningState.PREVIEW
                ):
                    break
            except Empty:
                pass

    def set_shutter(self, shutter_task, shutter_state):
        shutter_task.write(shutter_state, auto_start=True)

    def run_scanning(self):
        while not self.stop_event.is_set():
            self.scanning_parameters = self.new_parameters
            self.roi_parameters = self.new_roi_parameters
            self.compute_scan_parameters()
            with Task() as write_task, Task() as read_task, Task() as shutter_task:
                self.setup_tasks(read_task, write_task, shutter_task)
                self.set_shutter(shutter_task, self.scanning_parameters.shutter)
                if self.scanning_parameters.scanning_state == ScanningState.PAUSED:
                    self.set_shutter(shutter_task, False)
                    self.pause_loop()
                else:
                    self.scan_loop(read_task, write_task)


class ImageReconstructor(Process):
    def __init__(self, data_in_queue, stop_event, max_mbytes_queue=300):
        super().__init__()
        self.data_in_queue = data_in_queue
        self.parameter_queue = Queue()
        self.stop_event = stop_event
        self.output_queue = ArrayQueue(max_mbytes_queue)
        self.scanning_parameters = None
        self.waveform = None

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.scanning_parameters = self.parameter_queue.get(timeout=0.001)
                self.waveform = compute_waveform(self.scanning_parameters)
            except Empty:
                pass

            try:
                images = self.data_in_queue.get(timeout=0.001)
                recon_images = []
                for image in images:
                    recon_images.append(
                        scanning_patterns.reconstruct_image_pattern(
                            np.roll(image, self.scanning_parameters.mystery_offset),
                            *self.waveform,
                            (self.scanning_parameters.n_x, self.scanning_parameters.n_y),
                            self.scanning_parameters.n_bin,
                        )
                    )
                self.output_queue.put(np.stack(recon_images)
                )
            except Empty:
                pass
