from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Semi-Markov Visualizer")

        self.canvas = FigureCanvas(Figure())
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.plot()

    def plot(self):
        ax = self.canvas.figure.subplots()
        ax.plot([1, 2, 3], [4, 2, 6])
        self.canvas.draw()

app = QApplication([])
window = MainWindow()
window.show()
app.exec()