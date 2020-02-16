import zmq
from multiprocessing import Process
from lightparam.param_qt import ParameterTree


class ExternalCommunicationSettings(ParameterTree):
    def __init__(self):
        super().__init__()


class ExternalCommunication(Process):
    def __init__(self, experiment_start_event, external_parameters):
        super().__init__()
        self.experiment_start_event = experiment_start_event
        self.external_parameters = external_parameters  # not used
        self.zmq_tcp_address = 'tcp://192.168.233.72:5555'

    def run(self) -> None:
        zmq_context = zmq.Context()
        zmq_socket = zmq_context.socket(zmq.REQ)
        print(self.zmq_tcp_address)
        zmq_socket.connect(self.zmq_tcp_address)
        zmq_started = False
        while True:
            if self.experiment_start_event.is_set() and not zmq_started:
                try:
                    zmq_socket.send_json(self.external_parameters)
                    self.external_parameters['zmq_start'] = True
                    print('waiting for behaviour computer response')
                    duration = zmq_socket.recv_json()
                    print('Protocol lasts for {} seconds'.format(duration))
                    zmq_started = True

                except zmq.ZMQError:
                    print('0MQ connection unsuccessful')

