import pyvisa


class MotorControl:
    def __init__(
            self,
            port,
            baudrate=921600,
            parity=pyvisa.constants.Parity.none,
            encoding="ascii",
            axes=None,
    ):
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.axis = None
        axes = self.find_axis(axes)
        self.axes = str(axes)
        self.home_pos = None
        rm = pyvisa.ResourceManager()
        self.motor = rm.open_resource(
            port, baud_rate=baudrate, parity=parity, encoding=encoding, timeout=10
        )
        self.start_session()

    def get_position(self):
        input_m = self.axes + "TP"
        output = self.motor.query(input_m)
        output = [float(s) for s in output.split(",")]
        return output[0]

    def move_abs(self, displacement):
        displacement = str(displacement)
        command = self.axes + "PA" + displacement
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
        # return to home position
        # self.move_abs(self.home_pos)

        # motor off
        command = self.axes + "MF"
        self.execute_motor(command)

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
