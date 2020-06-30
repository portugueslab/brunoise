import pyvisa
from multiprocessing import Process
from queue import Empty


class MotorMaster(Process):

    def __init__(
            self,
            motors,
            input_queues,
            output_queues,
            close_setup_event,
    ):
        super().__init__()

        self.input_queues = input_queues
        self.output_queues = output_queues
        self.close_setup_event = close_setup_event
        self.motors = motors
        self.positions = dict.fromkeys(motors)
        self.motors_running = True
        self.get_positions()

    def run(self) -> None:
        while not self.close_setup_event.is_set():
            self.get_positions()
            self.move_motors()
        self.close_setups()

    def close_setups(self):
        for axis in self.motors.keys():
            self.motors[axis].end_session()

    def get_positions(self):
        for axis in self.motors.keys():
            actual_pos = self.motors[axis].get_position()
            if actual_pos is not None:
                self.positions[axis] = actual_pos
                self.output_queues[axis].put(actual_pos)

    def move_motors(self):
        for axis in self.motors.keys():
            package = self.get_last_entry(self.input_queues[axis])
            if package:
                mov_value = package[0]
                mov_type = package[1].name
                empty_queue = False
            else:
                empty_queue = True

            if empty_queue is False:
                if mov_type is "relative":
                    self.motors[axis].move_rel(mov_value)
                elif mov_type is "absolute":
                    self.motors[axis].move_abs(mov_value)

    @staticmethod
    def get_last_entry(queue):
        out = tuple()
        while True:
            try:
                out = queue.get(timeout=0.001)
            except Empty:
                break
        return out


class MotorControl:

    def __init__(
            self,
            port,
            baudrate=921600,
            parity=pyvisa.constants.Parity.none,
            encoding="ascii",
            axis=None,
    ):
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        axes = self.find_axis(axis)
        self.axes = str(axes)
        self.x = 0
        self.y = 0
        self.home_pos = None
        self.motor = None
        self.start_session()
        self.connection = True

    def get_position(self):
        if self.axes == 1:
            pos = self.x
        elif self.axes == 2:
            pos = self.y
        else:
            pos = 0
        return pos

    def move_rel(self, displacement=0.0):
        if self.axes == 1:
            self.x = self.x + displacement
        elif self.axes == 2:
            self.y = self.y + displacement
        else:
            pass

    def set_units(self, units):
        if units == "mm":
            units = 2
        elif units == "um":
            units = 3

    def define_home(self):
        self.home_pos = self.get_position()

    def go_home(self):
        pass

    def execute_motor(self, command):
        print("motor", self.axes, "moved to:", command)

    def start_session(self):
        # motor on
        print("motor", self.axes, "on")
        self.set_units("mm")

    def end_session(self):
        # motor off
        # command = self.axes + "MF"
        # self.execute_motor(command)
        # close connection
        print("motor", self.axes, "off")

    @staticmethod
    def find_axis(axes):
        if axes == "x":
            axes = 1
        elif axes == "y":
            axes = 2
        elif axes == "z":
            axes = 3
        return axes
