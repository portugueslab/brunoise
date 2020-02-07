from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from scanning import Scanner
from streaming_save import StackSaver

import pyqtgraph as pg
import numpy as np

import qdarkstyle

from queue import Empty
from lightparam import Param, Parametrized

class ExperimentSettings(Parametrized):
    def __init__(self):
        self.n_frames = Param(10, (1, 10000))
        self.n_planes = Param(1, (1, 500))

class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.scanner = Scanner()
        self.save_queue = ArrayQueue()
        self.saver = StackSaver()
        self.setLayout(QVBoxLayout())
        self.image_viewer = pg.ImageView()
        self.layout().addWidget(self.image_viewer)
        self.stop_button = QPushButton("Stop")
        self.layout().addWidget(self.stop_button)
        self.stop_button.clicked.connect(self.stop)
        self.image_viewer.setImage(np.ones((100,100)))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.scanner.start()
        self.first_image = True
        
        self.saving = False

    def update(self):
        try:
            current_image = - self.scanner.data_queue.get(timeout=0.001)
            self.image_viewer.setImage(current_image,
             autoLevels=self.first_image,
             autoRange=self.first_image,
             autoHistogramRange=self.first_image)
            self.first_image = False
            if self.saving:
                self.save_queue.put(current_image)
        except Empty:
            pass

    def start_recording(self):
        pass

    def stop(self):
        self.scanner.stop_event.set()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
