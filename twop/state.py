from multiprocessing import Event
from lightparam import Param
from lightparam.param_qt import ParametrizedQt
from scanning import Scanner, ScanningParameters, ScanningState
from streaming_save import StackSaver, SavingParameters
from arrayqueues.shared_arrays import ArrayQueue
from queue import Empty
from twop.objective_motor import MotorControl


class ExperimentSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.n_frames = Param(10, (1, 10000))
        self.n_planes = Param(1, (1, 500))


class ScanningSettings(ParametrizedQt):
    def __init__(self):
        super().__init__()
        self.resolution = Param(400, (40, 1024))
        self.voltage = Param(3.0, (0.3, 4.0))
        self.reset_shutter = Param(True)
        self.binning = Param(10, (1, 50))
        self.output_rate_khz = Param(500, (100, 2000))


def convert_params(st: ScanningSettings) -> ScanningParameters:
    """
    Converts the GUI scanning settings in parameters appropriate for the
    laser scanning

    """
    sp = ScanningParameters(
        voltage_x=st.voltage,
        voltage_y=st.voltage,
        n_x=st.resolution,
        n_y=st.resolution,
        sample_rate_out=st.output_rate_khz * 1000,
        reset_shutter=st.reset_shutter,
    )
    return sp


class ExperimentState:
    def __init__(self):
        self.experiment_start_event = Event()
        self.scanning_settings = ScanningSettings()
        self.experiment_settings = ExperimentSettings()
        self.scanner = Scanner(self.experiment_start_event)
        self.motors = dict()
        self.motors['x'] = MotorControl("COM6", axes='x')
        self.motors['y'] = MotorControl("COM6", axes='y')
        self.motors['z'] = MotorControl("COM6", axes='z')
        self.save_queue = ArrayQueue()
        self.saver = StackSaver(self.save_queue, self.scanner.stop_event)
        self.saving = False
        self.scanning_settings.sig_param_changed.connect(self.send_scan_params)
        self.scanning_settings.sig_param_changed.connect(self.send_save_params)
        self.scanner.start()
        self.saver.start()

    def open_setup(self):
        pass

    def start_experiment(self):
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.EXPERIMENT_RUNNING
        self.scanner.parameter_queue.put(params_to_send)
        self.send_save_params()
        self.saving = True
        self.saver.start_saving.set()
        self.experiment_start_event.set()

    def close_setup(self):
        # Return Newport rotatory servo to "Not referenced" AKA stand-by state
        self.scanner.stop_event.set()
        pass

    def get_image(self):
        try:
            image = -self.scanner.data_queue.get(timeout=0.001)
            if self.saving and self.saver.start_saving.is_set():
                self.save_queue.put(image)
            return image
        except Empty:
            return None

    def send_scan_params(self):
        self.scanner.parameter_queue.put(convert_params(self.scanning_settings))

    def send_save_params(self):
        self.saver.saving_parameter_queue.put(
            SavingParameters(
                output_dir=r"C:\Users\portugueslab\Desktop\test\python",
                plane_size=(
                    self.scanning_settings.resolution,
                    self.scanning_settings.resolution,
                ),
                n_t=self.experiment_settings.n_frames,
                n_z=self.experiment_settings.n_planes,
            )
        )
