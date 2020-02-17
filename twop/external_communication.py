import zmq
from multiprocessing import Process, Queue
from lightparam.param_qt import ParameterTree


class ExternalCommunicationSettings(ParameterTree):
    def __init__(self):
        super().__init__()


class ExternalCommunication(Process):
    def __init__(self, experiment_start_event, external_parameters, end_signal):
        super().__init__()
        self.end_signal = end_signal
        self.experiment_start_event = experiment_start_event
        self.external_parameters = external_parameters  # not used
        self.zmq_tcp_address = "tcp://192.168.233.72:5555"
        self.duration_queue = Queue()

    def run(self) -> None:
        zmq_context = zmq.Context()
        zmq_socket = zmq_context.socket(zmq.REQ)
        print(self.zmq_tcp_address)
        zmq_socket.connect(self.zmq_tcp_address)
        zmq_started = False
        while not self.end_signal.is_set():
            if self.experiment_start_event.is_set() and not zmq_started:
                try:
                    print("try send message")
                    zmq_socket.send_json(self.external_parameters)
                    self.external_parameters["zmq_start"] = True
                    print("waiting for behaviour computer response")
                    duration = zmq_socket.recv_json()
                    print("Protocol lasts for {} seconds".format(duration))
                    self.duration_queue.put(duration)
                    zmq_started = True

                except zmq.ZMQError:
                    print("0MQ connection unsuccessful")
