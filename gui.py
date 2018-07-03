#!/usr/bin/env python3
import sys
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction,
                             QHBoxLayout, QVBoxLayout, QGridLayout,
                             QLabel, QScrollArea, QPushButton, QFileDialog,
                             QCheckBox, QSlider, QLineEdit, QRubberBand)
from PyQt5.QtGui import QPixmap, QKeySequence
from search import find_holes, gaussianBlur


class ImageViewer(QScrollArea):

    def __init__(self, filename=''):
        super().__init__()
        self.initUI(filename)

    def initUI(self, filename):
        self.zoomScale = 1
        self.pixmap = QPixmap(filename) # for resizing
        self.originalCopy = self.pixmap # for cropping
        self.searchCopy = self.pixmap # display search matches
        self.blurredCopy = self.pixmap
        # QPixmap needs label to resize
        self.label = QLabel(self)
        self._refresh()
        self.setWidget(self.label)

    def loadPicture(self, img, newImg=False):
        if type(img) == str:
            self.pixmap.load(img)
        elif type(img) == QPixmap:
            self.pixmap = img
        else:
            raise TypeError("ImageViewer can't load img of type %s"
                            % type(img))
        if newImg:
            self.originalCopy = self.pixmap
            self.blurredCopy = gaussianBlur(self.originalCopy)
            self.zoomScale = 1
        self.searchCopy = self.pixmap
        self._refresh()

    def _refresh(self):
        self.pixmap = self.searchCopy.scaled(
                                     self.zoomScale * self.searchCopy.size(),
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

    def mousePressEvent(self, eventQMouseEvent):
        self.center = eventQMouseEvent.pos()
        self.rband = QRubberBand(QRubberBand.Rectangle, self)
        self.rband.setGeometry(QRect(self.center, QSize()))
        self.rband.show()

    def mouseMoveEvent(self, eventQMouseEvent):
        # unnormalized QRect can have negative width/height
        self.rband.setGeometry(QRect(2*self.center - eventQMouseEvent.pos(),
                               eventQMouseEvent.pos()).normalized())

    def mouseReleaseEvent(self, eventQMouseEvent):
        self.rband.hide()
        crop = self.rband.geometry()
        # handle misclick
        if crop.height() < 10 and crop.width() < 10:
            return
        # calculate X and Y position in original image
        X = int((self.horizontalScrollBar().value()+crop.x()) / self.zoomScale)
        Y = int((self.verticalScrollBar().value()+crop.y()) / self.zoomScale)
        origScaleCropWidth = int(crop.width() / self.zoomScale)
        origScaleCropHeight = int(crop.height() / self.zoomScale)
        # save crop
        cropQPixmap = self.originalCopy.copy(QRect(X, Y, origScaleCropWidth,
                                                         origScaleCropHeight))
        self.parentWidget().sidebar.cbBlurTemp.setCheckState(Qt.Unchecked)
        self.parentWidget().sidebar.crop_template.loadPicture(cropQPixmap,
                                                              newImg=True)


class Sidebar(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.width = 230
        self.setFixedWidth(self.width)
        self.sldPrec = 3
        self.thresholdVal = 0.8
        self.coords = []

        # widgets
        self.crop_template = ImageViewer()
        self.crop_template.setFixedHeight(200)
        self.cbBlurTemp = QCheckBox('Blur template')
        self.cbBlurTemp.clicked.connect(self.blurTemp)
        self.cbBlurImg  = QCheckBox('Blur image')
        self.cbBlurImg.clicked.connect(self.blurImg)
        buttonAutoDoc = QPushButton('Generate autodoc file')
        buttonAutoDoc.resize(buttonAutoDoc.sizeHint())
        buttonAutoDoc.clicked.connect(self.generateAutoDocFile)
        buttonPrintCoord = QPushButton('Print Coordinates')
        buttonPrintCoord.resize(buttonPrintCoord.sizeHint())
        buttonPrintCoord.clicked.connect(self.printCoordinates)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(10**self.sldPrec)
        self.slider.valueChanged.connect(self._setThreshDisp)
        self.threshDisp = QLineEdit()
        self.threshDisp.returnPressed.connect(
                          lambda: self._setSliderValue(self.threshDisp.text()))
        self.slider.setValue(self.thresholdVal * 10**self.sldPrec)
        buttonSearch = QPushButton('Search')
        buttonSearch.clicked.connect(self.templateSearch)

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(self.cbBlurTemp)
        vlay.addWidget(self.cbBlurImg)
        vlay.addWidget(QLabel())
        vlay.addWidget(QLabel('Threshold'))
        threshold = QGridLayout()
        threshold.addWidget(self.slider, 0, 0, 1, 1)
        threshold.addWidget(self.threshDisp, 1, 0, 1, 1)
        threshold.addWidget(buttonSearch)
        threshold.addWidget(QLabel())
        vlay.addLayout(threshold)
        vlay.addWidget(buttonAutoDoc)
        vlay.addWidget(buttonPrintCoord)
        vlay.addStretch(1)
        self.setLayout(vlay)

    def _setThreshDisp(self, i: int):
        self.thresholdVal = float("{:.{}f}".format(i / 10**self.sldPrec,
                                                   self.sldPrec))
        self.threshDisp.setText(str(self.thresholdVal))
        #print(self.thresholdVal)

    def _setSliderValue(self, s: str):
        try:
            self.slider.setValue(int(10**self.sldPrec * float(s)))
            self.thresholdVal = float("{:.{}f}".format(float(s), self.sldPrec))
            #print(self.thresholdVal)
        except ValueError:
            pass

    def blurTemp(self):
        if self.cbBlurTemp.isChecked():
            self.crop_template.loadPicture(self.crop_template.blurredCopy)
        else:
            self.crop_template.loadPicture(self.crop_template.originalCopy)

    def blurImg(self):
        if self.cbBlurImg.isChecked():
            self.parentWidget().viewer.loadPicture(
                                       self.parentWidget().viewer.blurredCopy)
        else:
            self.parentWidget().viewer.loadPicture(
                                       self.parentWidget().viewer.originalCopy)

    def templateSearch(self):
        #print(self.crop_template.pixmap.size())
        coords, template, img = find_holes(
                                     self.parentWidget().viewer.originalCopy,
                                     self.crop_template.pixmap,
                                     threshold=self.thresholdVal,
                                     blurTemplate=self.cbBlurTemp.isChecked(),
                                     blurImg=self.cbBlurImg.isChecked())
        self.coords = coords
        self.crop_template.loadPicture(template)
        self.parentWidget().viewer.loadPicture(img)

    def printCoordinates(self):
        print(self.coords)

    def generateAutoDocFile(self):
        pass


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


class MainWindow(QMainWindow):

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
        self.setWindowTitle('Title')
        self.show()

    def openFileDialog(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File')[0]

        print(filename)
        if filename:
            self.root.viewer.loadPicture(filename, newImg=True)
            self.root.sidebar.cbBlurImg.setCheckState(Qt.Unchecked)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
