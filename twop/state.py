from multiprocessing import Event


class ExperimentState:
    def __init__(self):
        self.experiment_start_event = Event()
        self.saving = False

    def start_experiment(self):
        pass