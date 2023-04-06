import zmq
from lightparam.param_qt import ParameterTree


class ExternalCommunicationSettings(ParameterTree):
    def __init__(self):
        super().__init__()


class ZMQcomm:
    def __init__(self, zmq_tcp_address="tcp://localhost:5555", timeout=2):
        self.zmq_tcp_address = zmq_tcp_address
        self.timeout = timeout

    def send(self, data):
        zmq_context = zmq.Context()
        with zmq_context.socket(zmq.REQ) as zmq_socket:
            # Prevents the socket/context from hanging indefinitely when there is no connection.
            zmq_socket.setsockopt(zmq.LINGER, 0)

            zmq_socket.connect(self.zmq_tcp_address)
            zmq_socket.send_json(data)
            poller = zmq.Poller()
            poller.register(zmq_socket, zmq.POLLIN)
            duration = None
            if poller.poll(5000):
                duration = zmq_socket.recv_json()
            zmq_socket.close()

        # Clean up the connection.
        zmq_context.term()
        zmq_context.destroy()
        return duration
