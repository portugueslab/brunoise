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
        self.external_parameters = external_parameters
        self.zmq_tcp_address = 'fe80::4da3:b111:31b8:ecb4%12'

    def run(self) -> None:
        zmq_context = zmq.Context()
        zmq_socket = zmq_context.socket(zmq.REQ)
        print(self.zmq_tcp_address)
        zmq_socket.connect(self.zmq_tcp_address)
        while True:
            if self.experiment_start_event.is_set():
                if not self.external_parameters['zmq_start']:
                    zmq_started = False

                if self.external_parameters['zmq_start'] and not zmq_started:
                    try:
                        zmq_socket.send_json(self.external_parameters)
                        self.external_parameters['zmq_start'] = False
                        print('waiting for behaviour computer response')
                        duration = zmq_socket.recv_json()
                        print('Protocol lasts for {} seconds'.format(duration))
                        zmq_started = True

                    except zmq.ZMQError:
                        print('0MQ connection unsuccessful')

