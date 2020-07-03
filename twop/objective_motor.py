import pyvisa
from multiprocessing import Process
from queue import Empty
from time import sleep

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
        self.get_positions(first=True)

    def run(self) -> None:
        for ax in self.motors.keys():
            self.motors[ax].open_communication()
        while not self.close_setup_event.is_set():
            self.get_positions()
            self.move_motors()
        self.close_setups()

    def close_setups(self):
        for axis in self.motors.keys():
            self.motors[axis].end_session()

    def get_positions(self, first=False):
        for axis in self.motors.keys():
            if not first:
                actual_pos = self.motors[axis].get_position()
            else:
                actual_pos = self.motors[axis].get_position(first=True)
            # print("actual pos mort", axis, actual_pos)
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
                if mov_type == "relative":
                    print(mov_value)
                    self.motors[axis].move_rel(mov_value)
                elif mov_type == "absolute":
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
        self.connection = True

    def get_position(self, first=False):
        if not first:
            input_m = self.axes + "TP"
            try:
                output = self.motor.query(input_m)
                try:
                    output = [float(s) for s in output.split(",")]
                except ValueError:
                    print("Got ", output, "from motor", self.axes, ",what to do?")
            except pyvisa.VisaIOError:
                print(f"Error get position axes number {self.axes} ")
                output = [None]
        else:
            output = [None]
        return output[0]

    def move_abs(self, coordinate):
        coordinate = str(coordinate)
        command = self.axes + "PA" + coordinate
        self.execute_motor(command)

    def move_rel(self, displacement=0.0):
        displacement = str(displacement)
        command = self.axes + "PR" + displacement
        self.execute_motor(command)

    def set_units(self, units):
        if units == "mm":
            units = 2
        elif units == "um":
            units = 3
        command = self.axes + "SN" + str(units)
        self.execute_motor(command)

    def define_home(self):
        self.home_pos = self.get_position()

    def go_home(self):
        command = self.axes + "OR" + str(2)
        self.execute_motor(command)

    def execute_motor(self, command):
        try:
            self.motor.query(command)
        except pyvisa.VisaIOError:
            pass

    def start_session(self):
        # motor on
        command = self.axes + "MO"
        self.execute_motor(command)

        # set trajectory mode to trapezoidal
        command = self.axes + "TJ" + str(1)
        self.execute_motor(command)

        # set jog high speed to 0.2 for x,y or to 0.5 for z
        if self.axes == "1" or self.axes == "2":
            command = self.axes + "JH" + str(0.2)
            self.execute_motor(command)
        elif self.axes == "3":
            command = self.axes + "JH" + str(0.5)
            self.execute_motor(command)

        # set jog low speed to 0.01
        command = self.axes + "TW" + str(0.01)
        self.execute_motor(command)

        # define home position
        self.define_home()

        # set mm as unit
        self.set_units("mm")

    def end_session(self):
        # motor off
        command = self.axes + "MF"
        self.execute_motor(command)
        # close connection
        self.motor.close()
        self.connection = False

    def open_communication(self):
        rm = pyvisa.ResourceManager()
        self.motor = rm.open_resource(
            self.port, baud_rate=self.baudrate, parity=self.parity,
            encoding=self.encoding, timeout=10
        )
        self.start_session()
        print(self.axes, "done")

    @staticmethod
    def find_axis(axes):
        if axes == "x":
            axes = 1
        elif axes == "y":
            axes = 2
        elif axes == "z":
            axes = 3
        return axes


class PreMotor:
    @staticmethod
    def query(self):
        return "None"
