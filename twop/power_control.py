import pyvisa
from math import acos


class LaserPowerControl:
    def __init__(
        self,
        port="COM5",
        baudrate=921600,
        parity=pyvisa.constants.Parity.none,
        encoding="ascii",
        device=1,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.baudrate = baudrate
        self.parity = parity
        self.encoding = encoding
        self.port = port
        self.device = device
        self.rotatory_stage = None
        self.execute_home_search()

    def get_position(self):
        device = "1"
        input_m = device + "TP"
        output = self.rotatory_stage.query(input_m)
        return output

    def execute_home_search(self):
        input_m = str(self.device) + "OR"
        print("power_control home search...")

    def get_upper_bound(self):
        upper_bound = ""
        input_m = str(self.device) + "SR" + upper_bound
        print("power_control get upper bound...")
        return 100

    def get_lower_bound(self):
        lower_bound = ""
        input_m = str(self.device) + "SL" + lower_bound
        print("power_control get lower bound...")
        return 0

    def move_abs(self, target_power_percent=0):
        target_position = self.unit_transformer(target_power_percent)
        input_m = str(self.device) + "PA" + str(target_position)
        print("Set power to:", target_position)

    def terminate_connection(self):
        self.rotatory_stage.close()

    @staticmethod
    def unit_transformer(
        target_power_percent,
        max_est_power=1088.318,
        min_est_power=1.753,
        amplitude=546.077,
        vertical_shift=0.997,
        frequency=0.07,
        phase_shift=53.097,
    ):
        # There is a notebook in the Demonstrations repository to calculate these values based on a sinusoidal function
        # This function maps power percentage to degrees, parameters were experimentally determined
        power_units = (max_est_power - min_est_power) * (
            target_power_percent / 100
        ) - min_est_power

        target_units: float = phase_shift + acos(
            power_units / amplitude - vertical_shift
        ) / frequency
        return target_units
