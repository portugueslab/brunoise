from multiprocessing import Event
from lightparam import Param
from lightparam.param_qt import ParametrizedQt
from scanning import Scanner, ScanningParameters, ScanningState
from streaming_save import StackSaver
from arrayqueues.shared_arrays import ArrayQueue


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
    ScanningParameters(
        voltage_x=st.voltage,
        voltage_y=st.voltage,
        n_x=st.resolution,
        n_y=st.resolution,
        sample_rate_out=st.output_rate_khz * 1000,
        reset_shutter=st.reset_shutter,
    )


class ExperimentState:
    def __init__(self):
        self.experiment_start_event = Event()
        self.scanning_settings = ScanningSettings()
        self.experiment_settings = ExperimentSettings()
        self.scanner = Scanner(self.experiment_start_event)
        self.save_queue = ArrayQueue()
        self.saver = StackSaver(self.save_queue, self.scanner.stop_event)
        self.saving = False
        self.scanning_settings.sig_param_changed.connect(self.send_new_params)

    def open_setup(self):
        pass

    def start_experiment(self):
        params_to_send = convert_params(self.scanning_settings)
        params_to_send.scanning_state = ScanningState.EXPERIMENT_RUNNING
        self.scanner.parameter_queue.put(params_to_send)
        self.saving = True
        self.experiment_start_event.set()

    def close_setup(self):
        # Return Newport rotatory servo to "Not referenced" AKA stand-by state
        self.scanner.stop_event.set()
        self.laser.terminate_connection()
        pass

    def get_image(self):
        image = self.scanner.data_queue.get(timeout=0.001)
        if self.saving:
            self.save_queue.put(image)
        return image

    def send_new_params(self):
        self.scanner.parameter_queue.put(convert_params(self.scanning_settings))
