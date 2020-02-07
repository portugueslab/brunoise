from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from scanning import Scanner

import pyqtgraph as pg
import numpy as np

import qdarkstyle

from queue import Empty
import lightparam


class TwopViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.scanner = Scanner()
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

    def update(self):
        try:
            current_image = - self.scanner.data_queue.get(timeout=0.001)
            self.image_viewer.setImage(current_image,
             autoLevels=self.first_image,
             autoRange=self.first_image,
             autoHistogramRange=self.first_image)
            self.first_image = False
        except Empty:
            pass

    def stop(self):
        self.scanner.stop_event.set()


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
