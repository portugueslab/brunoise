from multiprocessing import Event


class ExperimentState:
    def __init__(self):
        self.experiment_start_event = Event()
        self.saving = False

    def open_setup(self):
        pass

    def start_experiment(self):
        pass

    def close_setup(self):
        # Return Newport rotatory servo to "Not referenced" AKA stand-by state
        self.laser.terminate_connection()
        pass
