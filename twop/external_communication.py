import zmq
from multiprocessing import Process, Queue
from lightparam.param_qt import ParameterTree
from time import sleep

class ExternalCommunicationSettings(ParameterTree):
    def __init__(self):
        super().__init__()


class ExternalCommunication(Process):
    def __init__(self, experiment_start_event, end_signal):
        super().__init__()
        self.end_signal = end_signal
        self.experiment_start_event = experiment_start_event
        self.external_parameters = dict(scanning="new software")  # not used
        self.zmq_tcp_address = "tcp://O1-592:5555"
        self.duration_queue = Queue()

    def run(self) -> None:
        zmq_context = zmq.Context()
        zmq_socket = zmq_context.socket(zmq.REQ)
        zmq_socket.connect(self.zmq_tcp_address)
        zmq_started = False
        while not self.end_signal.is_set():
            if self.experiment_start_event.is_set() and not zmq_started:
                try:
                    zmq_socket.send_json(self.external_parameters)
                    self.external_parameters["zmq_start"] = True
                    print("ZMQ sent")
                    duration = zmq_socket.recv_json()
                    self.duration_queue.put(duration)
                    zmq_started = True

                except zmq.ZMQError:
                    print("0MQ connection unsuccessful")
            sleep(0.0001)
