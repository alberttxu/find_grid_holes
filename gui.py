#!/usr/bin/env python3
import sys
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction,
                             QHBoxLayout, QVBoxLayout, QGridLayout,
                             QLabel, QScrollArea, QPushButton, QFileDialog,
                             QCheckBox, QSlider, QLineEdit, QRubberBand)
from PyQt5.QtGui import QPixmap, QKeySequence


class ImageViewer(QScrollArea):

    def __init__(self, filename=''):
        super().__init__()
        self.initUI(filename)

    def initUI(self, filename):
        self.zoomScale = 1
        self.pixmap = QPixmap(filename)
        self.originalCopy = self.pixmap
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.label.sizeHint())
        self.setWidget(self.label)

    def loadPicture(self, filename):
        self.zoomScale = 1
        self.pixmap.load(filename)
        self.originalCopy = self.pixmap
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.pixmap.size())

    def _refresh(self):
        self.pixmap = self.originalCopy.scaled(
                                         self.zoomScale
                                         * self.originalCopy.size(),
                                         aspectRatioMode=Qt.KeepAspectRatio)
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.pixmap.size())

    def zoomIn(self):
        self.zoomScale += 0.1
        self._refresh()

    def zoomOut(self):
        self.zoomScale -= 0.1
        self._refresh()


class ImageViewerCrop(ImageViewer):

    def __init__(self, filename=''):
        super().__init__(filename)

    def mousePressEvent (self, eventQMouseEvent):
        self.originQPoint = eventQMouseEvent.pos()
        self.currentQRubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.currentQRubberBand.setGeometry(QRect(self.originQPoint, QSize()))
        self.currentQRubberBand.show()

    def mouseMoveEvent (self, eventQMouseEvent):
        self.currentQRubberBand.setGeometry(
                QRect(self.originQPoint, eventQMouseEvent.pos()).normalized())

    def mouseReleaseEvent (self, eventQMouseEvent):
        self.currentQRubberBand.hide()
        currentQRect = self.currentQRubberBand.geometry()
        self.currentQRubberBand.deleteLater()
        cropQPixmap = self.label.pixmap().copy(currentQRect)
        cropQPixmap.save('output.png')

        self.parentWidget().sidebar.crop_template.loadPicture('output.png')


class Sidebar(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.width = 230
        self.setFixedWidth(self.width)

        # widgets
        self.crop_template = ImageViewer('output.png')
        self.crop_template.setFixedHeight(200)
        blur_template = QCheckBox('Blur template')
        blur_img  = QCheckBox('Blur image')
        buttonAutoDoc = QPushButton('Generate autodoc file')
        buttonAutoDoc.resize(buttonAutoDoc.sizeHint())
        buttonPrintCoord = QPushButton('Print Coordinates')
        buttonPrintCoord.resize(buttonPrintCoord.sizeHint())
        slider = QSlider(Qt.Horizontal)
        self.thresholdDisplay = QLineEdit()
        slider.valueChanged.connect(self.changeThreshDisp)

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(blur_template)
        vlay.addWidget(blur_img)
        vlay.addWidget(QLabel())

        vlay.addWidget(QLabel('Threshold'))
        threshold = QGridLayout()
        threshold.addWidget(slider, 0, 0, 1, 1)
        threshold.addWidget(self.thresholdDisplay, 1, 0, 1, 1)
        threshold.addWidget(QLabel())
        vlay.addLayout(threshold)

        vlay.addWidget(buttonAutoDoc)
        vlay.addWidget(buttonPrintCoord)
        vlay.addStretch(1)
        self.setLayout(vlay)

    def changeThreshDisp(self, i: int):
        self.thresholdDisplay.setText("%.2f" % (i/100))


class MainWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.sidebar = Sidebar()
        self.viewer = ImageViewerCrop()

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addWidget(self.sidebar, 1, 0, 1, 1)
        self.grid.addWidget(self.viewer, 1, 1, 5, 5)
        self.setLayout(self.grid)


class Window(QMainWindow):

    def __init__(self):
        super().__init__()
        self.root = MainWidget()
        self.setCentralWidget(self.root)
        self.statusBar()
        self.initUI()

    def initUI(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        viewMenu = menubar.addMenu('View')

        openFile = QAction("Open File", self)
        openFile.setShortcut("Ctrl+O")
        openFile.setStatusTip("Open new File")
        openFile.triggered.connect(self.openFileDialog)
        fileMenu.addAction(openFile)

        zoomIn = QAction("Zoom In", self)
        zoomIn.setShortcut(Qt.Key_Equal)
        zoomIn.triggered.connect(self.root.viewer.zoomIn)
        zoomOut = QAction("Zoom Out", self)
        zoomOut.setShortcut(Qt.Key_Minus)
        zoomOut.triggered.connect(self.root.viewer.zoomOut)
        viewMenu.addAction(zoomIn)
        viewMenu.addAction(zoomOut)

        self.setGeometry(300, 300, 1000, 1000)
        self.setWindowTitle('Window')
        self.show()

    def openFileDialog(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File',
                            '/home/albertxu/git_projects/find_grid_holes')[0]
        #filename = QFileDialog.getOpenFileName(self, 'Open File', '/')[0]

        print(filename)
        if filename:
            self.root.viewer.loadPicture(filename)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = Window()
    sys.exit(app.exec_())
