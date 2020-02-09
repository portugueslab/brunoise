import pyvisa


class MotorControl:
    def __init__(
            self,
            port,
            baudrate=921600,
            parity=pyvisa.constants.Parity.none,
            encoding="ascii",
            axis=None
    ):
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.pos = self.get_position()
        self.axis = None
        if axis is not None:
            self.find_axis(axis)
            self.axis = axis
        rm = pyvisa.ResourceManager()
        self.motor = rm.open_resource(
            port, baud_rate=baudrate, parity=parity, encoding=encoding, timeout=10
        )

    def get_position(self):
        input_m = "TP"
        output = self.motor.query(input_m)
        output = [float(s) for s in output.split(",")]
        position = output[self.axis]
        return position

    def move_abs(self, displacement=0.0):
        axis = str(self.axis)
        displacement = str(displacement)
        command = axis + "PA" + displacement
        self.execute_motor(command)
        self.pos = self.get_position()

    def move_rel(self, displacement=0.0):
        axis = str(self.axis)
        displacement = str(displacement)
        command = axis + "PR" + displacement
        self.execute_motor(command)
        self.pos = self.get_position()

    def set_units(self, units):
        if units == "mm":
            units = 2
        elif units == "um":
            units = 3
        axis = str(self.axis)
        command = axis + "SN" + str(units)
        self.execute_motor(command)

    def define_home(self, pos):
        axis = str(self.axis)
        command = axis + "DH" + str(pos)
        self.execute_motor(command)

    def go_home(self):
        axis = str(self.axis)
        command = axis + "OR" + str(2)
        self.execute_motor(command)

    def execute_motor(self, command):
        try:
            self.motor.query(command)
        except pyvisa.VisaIOError:
            pass

    @staticmethod
    def find_axis(axis):
        if axis == "x":
            axis = 1
        elif axis == "y":
            axis = 2
        elif axis == "z":
            axis = 3
        return axis


if __name__ == "__main__":
    motor = MotorControl("COM1")
    pos = motor.get_position()
    print('set home at:', pos)
    motor.define_home(pos)
    motor.move_rel(displacement=0.1)
    pos = motor.get_position()
    print('move to:', pos)
    motor.go_home()
    pos = motor.get_position()
    print('new position after method:', pos)
