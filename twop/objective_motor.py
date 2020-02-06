import pyvisa

class MotorControl:
    def __init__(self, port, baudrate=921600, parity=pyvisa.constants.Parity.none, encoding="ascii"):
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.x = None
        self.y = None
        self.z = None
        rm = pyvisa.ResourceManager()
        self.motor = rm.open_resource(port, baud_rate=baudrate, parity=parity,
                          encoding=encoding)
        self.update_position()
        
    def update_position(self):
        input_m = 'TP'
        output = self.motor.query(input_m)
        output = [float(s) for s in output.split(',')]
        self.x = output[0]
        self.y = output[1]
        self.z = output[2]
    
    def move_abs(self, axes=None, displacement):
        axes = str(axes)
        displacement = str(displacement)
        input_m = axes + 'PA' + displacement
        try:
            self.motor.query(input_m)
            except pyvisa.VisaIOError:
                pass
        self.update_position()
        
    def  move_rel(self, axes=None, displacement):
        axes = str(axes)
        displacement = str(displacement)
        input_m = axes + 'PR' + displacement
        try:
            self.motor.query(input_m)
            except pyvisa.VisaIOError:
                pass
        self.update_position()
        
    def set_units(self, units, axes=None):   
        if units == 'mm':
            units = 2
            elif units == 'um':
                units = 3
        if axes is None:
            for ax in range(3):
                axes = str(axes)
                input_m = ax + 'SN' + units
                self.motor.query(input_m)
        else:
            axes = str(axes)
            input_m = axes + 'SN' + units
            self.motor.query(input_m)
                
    def get_units(self):
        pass
    
    def find_axes(self, axes):
        if axes == 'x':
            axes = 1
        elif axes == 'y':
            axes = 2
        elif axes == 'z':
            axes = 3
        elif axes is None:
            axes = None
        return axes           
        
        
                
        
        
        
