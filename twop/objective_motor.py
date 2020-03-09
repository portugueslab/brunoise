import pyvisa
from multiprocessing import Process, Queue, Event
from queue import Empty


class MotorControl:
    def __init__(
            self,
            port,
            input_commands_queue,
            baudrate=921600,
            parity=pyvisa.constants.Parity.none,
            encoding="ascii",
            axes=None,
    ):
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.input_commands_queue = input_commands_queue
        self.output_positions_queue = Queue()
        axes = self.find_axis(axes)
        self.axes = str(axes)
        self.home_pos = None
        rm = pyvisa.ResourceManager()
        self.motor = rm.open_resource(
                    port, baud_rate=baudrate, parity=parity, encoding=encoding, timeout=10
                )
        self.start_session()
        self.connection = True

    def update(self):
            actual_pos = self.get_position()
            self.output_positions_queue.put(actual_pos)
            try:
                mov = self.input_commands_queue.get(timeout=0.001)
            except Empty:
                mov = None

            if mov is not None:
                if mov[1] is False:
                    self.move_rel(mov[0])
                elif mov[1] is True:
                    self.move_abs(mov[0])

    def get_position(self):
        input_m = self.axes + "TP"
        try:
            output = self.motor.query(input_m)
            try:
                output = [float(s) for s in output.split(",")]
            except ValueError:
                print("Got ", output, "from motor, what to do?")
            return output[0]

        except pyvisa.VisaIOError:
            print(f"Error get position axes number {self.axes} ")
            return None

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

    @staticmethod
    def find_axis(axes):
        if axes == "x":
            axes = 1
        elif axes == "y":
            axes = 2
        elif axes == "z":
            axes = 3
        return axes


if __name__ == "__main__":
    motor = MotorControl("COM5", axes="x")
    pos = motor.get_position()
    print("start pos:", pos)
    new_pos = 0.01
    print("new pos:", new_pos)
    motor.move_abs(displacement=new_pos)
    try:
        motor.motor.query("1PA0.01")
    except pyvisa.VisaIOError:
        pass
    pos = motor.get_position()
    print("moved to:", pos)
