from PyQt5.QtWidgets import QApplication
import qdarkstyle
from brunoise.gui import TwopViewer
import click

@click.command()
def main():
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    viewer = TwopViewer()
    viewer.show()
    app.exec_()
