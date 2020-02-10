from multiprocessing import Event, Process, Queue
import numpy as np

import nidaqmx
from nidaqmx.stream_readers import AnalogMultiChannelReader, AnalogSingleChannelReader
from nidaqmx.stream_writers import AnalogMultiChannelWriter, AnalogSingleChannelWriter
from nidaqmx.constants import Edge, AcquisitionType

from arrayqueues.shared_arrays import ArrayQueue
from queue import Empty

import scanning_patterns
from copy import copy
from dataclasses import dataclass


@dataclass
class ScanningParameters:
    n_x: int = 400
    n_y: int = 400
    voltage_x: float = 3
    voltage_y: float = 3
    n_bin: int = 10
    sample_rate_out: float = 500000.0


class Scanner(Process):
    def __init__(self, max_queuesize=200):
        super().__init__()
        self.data_queue = ArrayQueue(max_mbytes=200)
        self.parameter_queue = Queue()
        self.stop_event = Event()
        self.scanning_parameters = ScanningParameters()
        self.new_parameters = copy(self.scanning_parameters)

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
        self.raw_x, self.raw_y = scanning_patterns.simple_scanning_pattern(
            self.n_x, self.n_y, 10, 300, True
        )
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
        self.read_buffer = np.zeros((2, self.n_samples_in))
        self.mystery_offset = (
            -400
        )  # an offset between reading and writing which seems constant

    def run_scanning(self):
        scanning_patterns.reconstruct_image_pattern(
            np.roll(self.read_buffer[0, :], self.mystery_offset),
            self.raw_x,
            self.raw_y,
            (self.n_y, self.n_x),
            self.n_bin,
        )

        while not self.stop_event.is_set():
            self.scanning_parameters = self.new_parameters
            self.compute_scan_parameters()
            with nidaqmx.Task() as write_task, nidaqmx.Task() as read_task:
                # Configure the channels
                read_task.ai_channels.add_ai_voltage_chan(
                    "Dev1/ai0:1", min_val=-5, max_val=5
                )  # channels are 0: green PMT, 1 x galvo pos 2 y galvo pos
                write_task.ao_channels.add_ao_voltage_chan(
                    "Dev1/ao0:1", min_val=-10, max_val=10
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

                writer = AnalogMultiChannelWriter(write_task.out_stream)
                reader = AnalogMultiChannelReader(read_task.in_stream)

                first_write = True
                while not self.stop_event.is_set():
                    # The first write has to be defined before the task starts
                    writer.write_many_sample(self.write_signals)
                    if first_write:
                        read_task.start()
                        write_task.start()
                        first_write = False
                    reader.read_many_sample(
                        self.read_buffer,
                        number_of_samples_per_channel=self.n_samples_in,
                        timeout=1,
                    )
                    self.data_queue.put(
                        scanning_patterns.reconstruct_image_pattern(
                            np.roll(self.read_buffer[0, :], self.mystery_offset),
                            self.raw_x,
                            self.raw_y,
                            (self.n_y, self.n_x),
                            self.n_bin,
                        )
                    )
                    try:
                        self.new_parameters = self.parameter_queue.get(timeout=0.0001)
                        if self.new_parameters != self.scanning_parameters:
                            break
                    except Empty:
                        pass
