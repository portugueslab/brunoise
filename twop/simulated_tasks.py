import numpy as np
import tifffile
from matplotlib import Path
import flammkuchen as fl
from time import sleep

class ShutterTask:
    def __init__(self):
        self.open = False
        self.auto_start = None

    def write(self, command, auto_start = None):
        self.open = command
        self.auto_start = auto_start

class WriteTask:
    def __init__(self):
        pass

    def start(self):
        return True

    def write_many_sample(self, signal):
        pass


class ReadTask:
    def __init__(self, type_exp):
        self.time_loop = 0
        self.master_path = Path(r"C:\Users\Asus\Desktop\sim_exp") / type_exp
        list_files = list(self.master_path.glob("*"))
        self.sim_path = list_files[0]
        if self.sim_path.suffix == ".tif":
            self.data = tifffile.imread(str(self.sim_path))
            print(self.data.shape)
        elif self.sim_path.suffix == ".h5":
            self.data = fl.load(str(self.sim_path))["stack_4D"][:, 0, :, :]

    def start(self):
        return True

    def read_many_sample(self, first_write):
        if first_write is True:
            self.time_loop = 0
        frame = self.data[self.time_loop, :, :]
        if self.time_loop == self.data.shape[0] - 1:
            self.time_loop = 0
        else:
            self.time_loop += 1
            sleep(0.05)
        return frame
