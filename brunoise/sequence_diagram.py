from multiprocessing import Queue
from collections import namedtuple
from time import time_ns

SequenceElement = namedtuple("SequenceElement", "source t event")


class SequenceDiagram:
    def __init__(self, queue: Queue, source: str):
        self.queue = queue
        self.source = source

    def put(self, message):
        self.queue.put(SequenceElement(self.source, time_ns(), message))
