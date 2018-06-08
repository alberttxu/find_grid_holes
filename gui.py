#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction, 
                             QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
                             QGridLayout, QFileDialog)
from PyQt5.QtGui import QIcon, QPixmap

class ImageViewer(QWidget):

    def __init__(self, filename):
        super().__init__()
        self.initUI(filename)

    def initUI(self, filename):
        self.pixmap = QPixmap(filename)
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        #self.show()

    def refresh(self, filename):
        self.pixmap.load(filename)
        self.label.setPixmap(self.pixmap)


class Sidebar(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        b1 = QPushButton('ok', self)
        b1.resize(b1.sizeHint())
        b2 = QPushButton('ok', self)
        b2.resize(b2.sizeHint())
        
        vlay = QVBoxLayout()
        vlay.addWidget(b1)
        vlay.addWidget(b2)
        self.setLayout(vlay)


class MainWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self, filename='mesh_6.jpg'):
        self.sidebar = Sidebar()
        self.viewer = ImageViewer(filename)

        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.grid.addWidget(self.sidebar, 1, 0, 1, 1)
        self.grid.addWidget(self.viewer, 1, 1, 5, 5)
        self.setLayout(self.grid)
        self.setLayout(self.grid)

    def loadPicture(self, filename):
        self.viewer.refresh(filename)
        

class Window(QMainWindow):

    def __init__(self):
        super().__init__()
        self.root = MainWidget()
        self.setCentralWidget(self.root)
        self.initUI()

    def initUI(self):
        openFile = QAction("Open File", self)
        openFile.triggered.connect(self.openFileDialog)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFile)

        self.setGeometry(300, 300, 1000, 1000)
        self.setWindowTitle('Window')
        self.show()

    def openFileDialog(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File', '/home/albertxu/git_projects/find_grid_holes')[0]

        print(filename)
        if filename:
            self.root.loadPicture(filename)
        

if __name__ == '__main__':
        
    app = QApplication(sys.argv)
    w = Window()
    sys.exit(app.exec_())
