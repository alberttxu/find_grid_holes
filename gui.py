#!/usr/bin/env python3
import io
import sys
import cv2
import numpy as np
from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt5.QtCore import Qt, QRect, QSize, QBuffer
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction,
                             QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
                             QScrollArea, QPushButton, QFileDialog, QCheckBox,
                             QSlider, QLineEdit, QRubberBand, QMessageBox,
                             QInputDialog, QDoubleSpinBox)
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QPalette, QBrush
from search import templateMatch
from autodoc import (isValidAutodoc, isValidLabel, sectionAsDict,
                     coordsToNavPoints)


# image data manipulation
def npToQImage(ndArr):
    return QPixmap.fromImage(ImageQt(Image.fromarray(ndArr))).toImage()

def qImgToPilRGBA(qimg):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qimg.save(buf, "PNG")
    return Image.open(io.BytesIO(buf.data().data())).convert('RGBA')

def qImgToNp(qimg):
    return np.array(qImgToPilRGBA(qimg))

def gaussianBlur(qimg, radius=5):
    pilImg = qImgToPilRGBA(qimg).filter(ImageFilter.GaussianBlur(radius))
    return QPixmap.fromImage(ImageQt(pilImg)).toImage()

def drawCross(img: 'ndarray', x, y):
    blue = (0,0,255,255)
    cv2.line(img, (x-10,y), (x+10,y), blue, 3)
    cv2.line(img, (x,y-10), (x,y+10), blue, 3)

def drawCrosses(img: 'ndarray', coords):
    img = np.flip(img, 0).copy()
    for x, y in coords:
        drawCross(img, x, y)
    return np.flip(img, 0).copy()

def drawCoords(qimg, coords):
    return npToQImage(drawCrosses(qImgToNp(qimg), coords))

# popup messages
def popup(parent, message):
    messagebox = QMessageBox(parent)
    messagebox.setText(message)
    messagebox.show()


class ImageViewer(QScrollArea):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.zoom = 1
        self.originalImg = QImage()
        self.blurredImg = QImage()
        self.activeImg = QImage()

        # need QLabel to setPixmap for images
        self.label = QLabel(self)
        self._refresh()
        self.setWidget(self.label)

    def _refresh(self):
        # save slider values to calculate new positions after zoom
        hBar = self.horizontalScrollBar()
        vBar = self.verticalScrollBar()
        try:
            hBarRatio = hBar.value() / hBar.maximum()
            vBarRatio = vBar.value() / vBar.maximum()
        except ZeroDivisionError:
            hBarRatio = 0
            vBarRatio = 0
        # resize
        img = self.activeImg.scaled(self.zoom * self.activeImg.size(),
                                    aspectRatioMode=Qt.KeepAspectRatio)
        self.label.setPixmap(QPixmap(img))
        self.label.resize(img.size())
        self.label.repaint()
        hBar.setValue(int(hBarRatio * hBar.maximum()))
        vBar.setValue(int(vBarRatio * vBar.maximum()))

    def _setActiveImg(self, img):
        self.activeImg = img
        self._refresh()

    def newImg(self, img):
        self.zoom = 1
        self.originalImg = img
        self.blurredImg = gaussianBlur(self.originalImg)
        self._setActiveImg(self.originalImg)

    def toggleBlur(self, toggle):
        if toggle:
            self._setActiveImg(self.blurredImg)
        else:
            self._setActiveImg(self.originalImg)

    def zoomIn(self):
        self.zoom *= 1.25
        self._refresh()

    def zoomOut(self):
        self.zoom *= 0.8
        self._refresh()


class ImageViewerCrop(ImageViewer):

    def __init__(self):
        super().__init__()
        self.searchedImg = QImage()
        self.searchedBlurImg = QImage()

    def openFile(self, filename):
        self.zoom = 1
        self.originalImg.load(filename)
        self.blurredImg = gaussianBlur(self.originalImg)
        self.parentWidget().sidebar._clearPts()

    def toggleBlur(self, toggle):
        if self.parentWidget().sidebar.coords:
            if toggle:
                self._setActiveImg(self.searchedBlurImg)
            else:
                self._setActiveImg(self.searchedImg)
        else:
            super().toggleBlur(toggle)

    def mousePressEvent(self, mouseEvent):
        self.shiftPressed = QApplication.keyboardModifiers() == Qt.ShiftModifier
        self.center = mouseEvent.pos()
        self.rband = QRubberBand(QRubberBand.Rectangle, self)
        self.rband.setGeometry(QRect(self.center, QSize()))
        self.rband.show()

    def mouseMoveEvent(self, mouseEvent):
        # make rubber band blue (only works on windows os)
        palette = QPalette()
        palette.setBrush(QPalette.Highlight, QBrush(Qt.blue))

        # unnormalized QRect can have negative width/height
        crop = QRect(2*self.center - mouseEvent.pos(),
                     mouseEvent.pos()).normalized()
        if self.shiftPressed:
            largerSide = max(crop.width(), crop.height())
            self.rband.setGeometry(self.center.x() - largerSide//2,
                                   self.center.y() - largerSide//2,
                                   largerSide, largerSide)
        else:
            self.rband.setGeometry(crop)
        self.rband.setPalette(palette)

    def mouseReleaseEvent(self, mouseEvent):
        self.rband.hide()
        crop = self.rband.geometry()
        if self.originalImg.isNull(): # no image loaded in
            return
        # handle single click initializing default QRect selecting entire image
        if crop.height() < 10 and crop.width() < 10:
            return
        # calculate X and Y position in original image
        X = int((self.horizontalScrollBar().value()+crop.x()) / self.zoom)
        Y = int((self.verticalScrollBar().value()+crop.y()) / self.zoom)
        origScaleCropWidth = int(crop.width() / self.zoom)
        origScaleCropHeight = int(crop.height() / self.zoom)
        # save crop
        cropQImage = self.originalImg.copy(QRect(X, Y, origScaleCropWidth,
                                                         origScaleCropHeight))
        sidebar = self.parentWidget().sidebar
        sidebar.cbBlurTemp.setCheckState(Qt.Unchecked)
        sidebar.crop_template.newImg(cropQImage)


class Sidebar(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.width = 230
        self.setFixedWidth(self.width)
        self.sldPrec = 3
        self.thresholdVal = 0.8
        self.pixelSizeNm = 10 # nanometers per pixel
        self.groupPoints = True
        self.groupRadius = 7 # µm
        self.lastGroupSize = 0
        self.lastMapLabel = ''
        self.lastStartLabel = 0
        self.generatedNav = ''
        self.coords = []

        # widgets
        self.crop_template = ImageViewer()
        self.crop_template.setFixedHeight(200)
        self.cbBlurTemp = QCheckBox('Blur template')
        self.cbBlurTemp.clicked.connect(self.blurTemp)
        self.cbBlurImg  = QCheckBox('Blur image')
        self.cbBlurImg.clicked.connect(self.blurImg)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(10**self.sldPrec)
        self.slider.valueChanged.connect(self._setThreshDisp)
        self.threshDisp = QDoubleSpinBox()
        self.threshDisp.setMaximum(1)
        self.threshDisp.setSingleStep(0.05)
        self.threshDisp.setDecimals(self.sldPrec)
        self.threshDisp.valueChanged.connect(
                         self._setThreshSlider)
        self.threshDisp.setValue(0.8)
        buttonSearch = QPushButton('Search')
        buttonSearch.clicked.connect(self._templateSearch)
        buttonPrintCoord = QPushButton('Print Coordinates')
        buttonPrintCoord.resize(buttonPrintCoord.sizeHint())
        buttonPrintCoord.clicked.connect(self.printCoordinates)
        buttonClearPts = QPushButton('Clear Points')
        buttonClearPts.clicked.connect(self._clearPts)
        buttonNewNavFile = QPushButton('Generate new nav file')
        buttonNewNavFile.resize(buttonNewNavFile.sizeHint())
        buttonNewNavFile.clicked.connect(self.generateNavFile)
        buttonAppendNav = QPushButton('Append to new nav file')
        buttonAppendNav.resize(buttonNewNavFile.sizeHint())
        buttonAppendNav.clicked.connect(self.appendToNavFile)
        self.cbGroupPoints = QCheckBox('Group points')
        self.cbGroupPoints.setCheckState(Qt.Checked)
        self.cbGroupPoints.clicked.connect(self._toggleGroupPoints)
        self.groupRadiusLineEdit = QLineEdit()
        self.groupRadiusLineEdit.returnPressed.connect(
                 lambda: self._setGroupRadius(self.groupRadiusLineEdit.text()))
        self._setGroupRadius(str(self.groupRadius))
        self.pixelSizeLineEdit = QLineEdit()
        self.pixelSizeLineEdit.returnPressed.connect(
                 lambda: self._setPixelSize(self.pixelSizeLineEdit.text()))
        self._setPixelSize(str(self.pixelSizeNm))

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(self.cbBlurTemp)
        vlay.addWidget(self.cbBlurImg)
        vlay.addWidget(QLabel())
        vlay.addWidget(QLabel('Threshold'))
        vlay.addWidget(self.slider)
        vlay.addWidget(self.threshDisp)
        vlay.addWidget(buttonSearch)
        vlay.addWidget(buttonPrintCoord)
        vlay.addWidget(buttonClearPts)
        vlay.addWidget(QLabel())
        #groupPtsLay = QHBoxLayout()
        groupPtsLay = QGridLayout()
        groupPtsLay.addWidget(self.cbGroupPoints, 1, 0)
        groupPtsLay.addWidget(QLabel('Group Radius'), 2, 0)
        groupPtsLay.addWidget(self.groupRadiusLineEdit, 2, 1)
        groupPtsLay.addWidget(QLabel('µm'), 2, 2)
        groupPtsLay.addWidget(QLabel('PixelSize'), 3, 0)
        groupPtsLay.addWidget(self.pixelSizeLineEdit, 3, 1)
        groupPtsLay.addWidget(QLabel('nm'), 3, 2)
        vlay.addWidget(buttonNewNavFile)
        vlay.addWidget(buttonAppendNav)
        vlay.addLayout(groupPtsLay)
        vlay.addStretch(1)
        self.setLayout(vlay)

    def blurTemp(self):
        self.crop_template.toggleBlur(self.cbBlurTemp.isChecked())

    def blurImg(self):
        self.parentWidget().viewer.toggleBlur(self.cbBlurImg.isChecked())

    def _setThreshDisp(self, i: int):
        self.threshDisp.setValue(i / 10**self.sldPrec)

    def _setThreshSlider(self, val: float):
        try:
            self.slider.setValue(int(10**self.sldPrec * val))
            self.thresholdVal = val
        except ValueError:
            pass

    def _templateSearch(self):
        templ = (self.crop_template.blurredImg if self.cbBlurTemp.isChecked()
                    else self.crop_template.originalImg)
        img = (self.parentWidget().viewer.blurredImg
               if self.cbBlurImg.isChecked()
               else self.parentWidget().viewer.originalImg)
        if img.isNull() or templ.isNull():
            popup(self, "either image or template missing")
            return

        self.coords = templateMatch(qImgToNp(img), qImgToNp(templ),
                                self.thresholdVal)
        viewer = self.parentWidget().viewer
        viewer.searchedImg = drawCoords(viewer.originalImg, self.coords)
        viewer.searchedBlurImg = drawCoords(viewer.blurredImg, self.coords)
        viewer._setActiveImg(viewer.searchedBlurImg
                             if self.cbBlurImg.isChecked()
                             else viewer.searchedImg)
        self.repaint()

    def printCoordinates(self):
        popup(self, f"{len(self.coords)} points: {str(self.coords)}")

    def _clearPts(self):
        self.coords = []
        self.cbBlurImg.setCheckState(Qt.Unchecked)
        viewer = self.parentWidget().viewer
        viewer._setActiveImg(viewer.originalImg)
        viewer.searchedImg = QImage()
        viewer.searchedBlurImg = QImage()
        viewer._refresh()

    def generateNavFile(self):
        self._writeToNavFile(isNew=True)

    def appendToNavFile(self):
        self._writeToNavFile(isNew=False)

    def _writeToNavFile(self, isNew):
        # error checking
        navfileLines = self.parentWidget().parentWidget().navfileLines
        if not navfileLines: # not loaded in
            print("navfile not loaded in")
            popup(self, "navfile not loaded in")
            return
        mapLabel, okClicked = QInputDialog.getText(self, "label number",
                                          "enter label # of map to merge onto",
                                          text=self.lastMapLabel)
        if not okClicked: return
        if not isValidLabel(navfileLines, mapLabel):
            popup(self, "label not found")
            return
        startLabel, okClicked = QInputDialog.getInt(self, "label number",
                                          "enter starting label of new items",
                                          value=self.lastStartLabel
                                                + self.lastGroupSize)
        if not okClicked: return
        if isNew:
            filename = QFileDialog.getSaveFileName(self, "Save points")[0]
            if filename == '' : return

        # write to file
        mapSection = sectionAsDict(navfileLines, mapLabel)
        groupRadiusPixels = 1000 * self.groupRadius / self.pixelSizeNm
        navPoints, numGroups = coordsToNavPoints(self.coords, mapSection,
                                                 startLabel, self.groupPoints,
                                                 groupRadiusPixels)
        if isNew:
            with open(filename, 'w') as f:
                f.write('AdocVersion = 2.00\n\n')
                for navPoint in navPoints:
                    f.write(navPoint.toString())
            popup(self, "nav file created")
            self.generatedNav = filename
        else:
            with open(self.generatedNav, 'a') as f:
                for navPoint in navPoints:
                    f.write(navPoint.toString())
            popup(self, "points added to nav file")
        # update fields
        self.lastGroupSize = numGroups
        self.lastStartLabel = startLabel
        self.lastMapLabel = mapLabel

    def _toggleGroupPoints(self):
        self.groupPoints = self.cbGroupPoints.isChecked()

    def _setGroupRadius(self, s: str):
        try:
            self.groupRadius = float("{:.1f}".format(float(s)))
            self.groupRadiusLineEdit.setText(str(self.groupRadius))
        except:
            pass

    def _setPixelSize(self, s: str):
        try:
            self.pixelSizeNm = float("{:.1f}".format(float(s)))
            self.pixelSizeLineEdit.setText(str(self.pixelSizeNm))
        except:
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
        filename = QFileDialog.getOpenFileName(self, 'Open Image')[0]

        print(filename)
        if filename:
            try:
                self.root.viewer.openFile(filename)
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
            popup(self, "could not read in nav file")
            return



if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
