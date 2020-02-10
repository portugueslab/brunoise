import pyvisa
from math import acos


class LaserPowerControl:

    def __init__(self, port='COM5', parity=pyvisa.constants.Parity.none, encoding="ascii"):
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.position = self.update_position()
        self.rm = pyvisa.ResourceManager()
        self.rotatory_stage = self.rm.open_resource(
            port,
            parity=parity,
            encoding=encoding,
            timeout=10,
            resource_name='laser_power_control'
        )
        self.execute_home_search()
        self.get_upper_bound()
        self.get_lower_bound()

    def update_position(self):
        device = '1'
        input_m = device + 'TP'
        output = self.rotatory_stage.query(input_m)
        return output

    def execute_home_search(self):
        device = '1'
        input_m = device + 'OR'
        self.rotatory_stage.query(input_m)

    def get_upper_bound(self):
        device = '1'
        upper_bound = ''
        input_m = device + 'SR' + upper_bound
        self.rotatory_stage.query(input_m)

    def get_lower_bound(self):
        device = '1'
        lower_bound = ''
        input_m = device + 'SL' + lower_bound
        self.rotatory_stage.query(input_m)

    def move_abs(self, target_power_percent=0):
        target_position = self.unit_transformer(target_power_percent)
        device = '1'
        input_m = device + 'PA' + str(target_position)
        self.rotatory_stage.query(input_m)

    def terminate_connection(self):
        self.rm.close()

    @staticmethod
    def unit_transformer(
            target_power_percent,
            max_est_power=1088.318,
            min_est_power=1.753,
            amplitude=546.077,
            vertical_shift=0.997,
            frequency=0.07,
            phase_shift=53.097
    ):
        # minimum and maximum power values are estimated based on model
        # this function maps power percentage to degrees, parameters were phenomenologically determined
        power_units = (max_est_power - min_est_power) * (target_power_percent / 100) - min_est_power
        target_units: float = phase_shift + acos(power_units / amplitude - vertical_shift) / frequency
        return target_units
