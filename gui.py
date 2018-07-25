#!/usr/bin/env python3
import io
import sys
import numpy as np
from PyQt5.QtCore import Qt, QRect, QSize, QBuffer
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction,
                             QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
                             QScrollArea, QPushButton, QFileDialog, QCheckBox,
                             QSlider, QLineEdit, QRubberBand, QMessageBox,
                             QInputDialog)
from PyQt5.QtGui import QImage, QPixmap, QKeySequence
from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from search import find_holes
from autodoc import (NavFilePoint, isValidAutodoc, isValidLabel, sectionAsDict,
                     createNav)


# image data manipulation
def npToQImage(ndArr):
    return QImage(ImageQt(Image.fromarray(ndArr)))

def QImageToPilRGBA(qimg):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(buf.data().data())).convert('RGBA')

def gaussianBlur(qimg):
    pilImg = QImageToPilRGBA(qimg).filter(ImageFilter.GaussianBlur)
    return QPixmap.fromImage(ImageQt(pilImg)).toImage()

# popup messages
def popup(parent, message):
    messagebox = QMessageBox(parent)
    messagebox.setText(message)
    messagebox.show()


class ImageViewer(QScrollArea):

    def __init__(self, filename=''):
        super().__init__()
        self.initUI(filename)

    def initUI(self, filename):
        self.zoomScale = 1
        self.img = QImage(filename) # for resizing
        self.originalCopy = self.img # for cropping
        self.searchCopy = self.img # display search matches
        self.blurredCopy = self.img
        # QImage needs label to resize
        self.label = QLabel(self)
        self._refresh()
        self.setWidget(self.label)
        #self.setAlignment(Qt.AlignCenter)

    def loadPicture(self, img, newImg=False):
        if type(img) == str:
            self.img.load(img)
        elif type(img) == QImage:
            self.img = img
        else:
            raise TypeError("ImageViewer can't load img of type %s"
                            % type(img))
        if newImg:
            self.originalCopy = self.img
            self.blurredCopy = gaussianBlur(self.originalCopy)
            self.zoomScale = 1
        self.searchCopy = self.img
        self._refresh()

    def toggleBlur(self, toggle):
        if toggle:
            self.loadPicture(self.blurredCopy)
        else:
            self.loadPicture(self.originalCopy)

    def _refresh(self):
        # save old slider values to recalculate
        hBar = self.horizontalScrollBar()
        vBar = self.verticalScrollBar()
        try:
            hBarRatio = hBar.value() / hBar.maximum()
            vBarRatio = vBar.value() / vBar.maximum()
        except ZeroDivisionError:
            hBarRatio = 0
            vBarRatio = 0
        # resize
        self.img = self.searchCopy.scaled(
                                     self.zoomScale * self.searchCopy.size(),
                                     aspectRatioMode=Qt.KeepAspectRatio)
        self.label.setPixmap(QPixmap(self.img))
        self.label.resize(self.img.size())
        self.label.repaint()
        hBar.setValue(int(hBarRatio * hBar.maximum()))
        vBar.setValue(int(vBarRatio * vBar.maximum()))

    def zoomIn(self):
        self.zoomScale *= 1.25
        self._refresh()

    def zoomOut(self):
        self.zoomScale *= 0.8
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
        cropQImage = self.originalCopy.copy(QRect(X, Y, origScaleCropWidth,
                                                         origScaleCropHeight))
        sb = self.parentWidget().sidebar
        sb.cbBlurTemp.setCheckState(Qt.Unchecked)
        sb.crop_template.loadPicture(cropQImage, newImg=True)


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
        buttonSearch.clicked.connect(self._templateSearch)

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

    def _setSliderValue(self, s: str):
        try:
            self.slider.setValue(int(10**self.sldPrec * float(s)))
            self.thresholdVal = float("{:.{}f}".format(float(s), self.sldPrec))
        except ValueError:
            pass

    def blurTemp(self):
        self.crop_template.toggleBlur(self.cbBlurTemp.isChecked())

    def blurImg(self):
        self.parentWidget().viewer.toggleBlur(self.cbBlurImg.isChecked())

    def _templateSearch(self):
        templ = (self.crop_template.blurredCopy if self.cbBlurTemp.isChecked()
                    else self.crop_template.originalCopy)
        img = (self.parentWidget().viewer.blurredCopy
               if self.cbBlurImg.isChecked()
               else self.parentWidget().viewer.originalCopy)

        try:
            self.coords, img_ndArr = find_holes(np.array(QImageToPilRGBA(img)),
                                          np.array(QImageToPilRGBA(templ)),
                                          threshold=self.thresholdVal)
            img = npToQImage(img_ndArr)
            self.parentWidget().viewer.loadPicture(img)
        except:
            popup(self, "either image or template missing")

    def printCoordinates(self):
        popup(self, f"{len(self.coords)} points: {str(self.coords)}")

    def generateAutoDocFile(self):
        navfileLines = self.parentWidget().parentWidget().navfileLines
        if not navfileLines: # not loaded in
            print("navfile not loaded in")
            popup(self, "navfile not loaded in")
            return
        mapLabel, okClicked = QInputDialog.getText(self, "label number",
                                          "enter label # of map to merge onto")
        if not okClicked: return
        if not isValidLabel(navfileLines, mapLabel):
            popup(self, "label not found")
            return
        filename = QFileDialog.getSaveFileName(self, "Save points")[0]
        mapSection = sectionAsDict(navfileLines, mapLabel)
        regis = int(mapSection['Regis'][0])
        drawnID = int(mapSection['MapID'][0])
        zHeight = float(mapSection['StageXYZ'][2])
        startLabel, okClicked = QInputDialog.getInt(self, "label number",
                                          "enter starting label of new items")
        if not okClicked:
            return
        createNav(filename, self.coords, zHeight, startLabel, regis, drawnID)
        popup(self, "autodoc created")


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
        self.navfile = ''
        self.navfileLines = []

    def initUI(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        viewMenu = menubar.addMenu('View')

        openFile = QAction("Open Image", self)
        openFile.setShortcut("Ctrl+O")
        openFile.setStatusTip("Open new Image")
        openFile.triggered.connect(self.imgFileDialog)
        loadNavFile = QAction("Load Nav File", self)
        loadNavFile.setStatusTip("Required: read in nav file to merge into")
        loadNavFile.triggered.connect(self.navFileDialog)
        fileMenu.addAction(openFile)
        fileMenu.addAction(loadNavFile)

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

    def imgFileDialog(self):
        print(self)
        filename = QFileDialog.getOpenFileName(self, 'Open Image')[0]

        print(filename)
        if filename:
            try:
                self.root.viewer.loadPicture(filename, newImg=True)
                self.root.sidebar.cbBlurImg.setCheckState(Qt.Unchecked)
            except:
                popup(self, "could not load image")

    def navFileDialog(self):
        navfile = QFileDialog.getOpenFileName(self, 'Load Nav File')[0]
        print(navfile)
        if not navfile: return
        if isValidAutodoc(navfile):
            popup(self, "successfully read in navfile")
            self.navfile = navfile
            with open(navfile) as f:
                lines = [line.strip() for line in f.readlines()]
                self.navfileLines = lines
        else:
            popup(self, "could not find AdocVersion")
            return



if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
