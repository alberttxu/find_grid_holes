#!/usr/bin/env python3
import io
import numpy as np
import cv2
from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QBuffer


def npToQpixmap(ndArr):
    return QPixmap.fromImage(ImageQt(Image.fromarray(ndArr)))

def QPixmapToPilRGBA(qpixmap):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qpixmap.save(buf, "PNG")
    return Image.open(io.BytesIO(buf.data().data())).convert('RGBA')

def gaussianBlur(qpixmap):
    pilImg = QPixmapToPilRGBA(qpixmap).filter(ImageFilter.GaussianBlur)
    return QPixmap.fromImage(ImageQt(pilImg))

# prevent including the same hole multiple times
def withinRadius(pt, coords, radius):
    x, y = pt
    if len(coords) == 0:
        return False
    for c in coords:
        distance = ((c[0]-x)**2 + (c[1]-y)**2) ** 0.5
        if distance < radius:
            return True
    return False

# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def find_holes(qpixImg, qpixTemplate, threshold=0.8,
               blurTemplate=False, blurImg=False):
    """returns QPixmap with green square around matches"""
    img = QPixmapToPilRGBA(qpixImg)
    template = QPixmapToPilRGBA(qpixTemplate)

    if blurImg:
        img = img.filter(ImageFilter.GaussianBlur)
    img = np.array(img)
    if blurTemplate:
        template = template.filter(ImageFilter.GaussianBlur)
    template = np.array(template)

    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)

    matches = []
    pastPoints = []
    for x, y, _ in scoresIndex:
        if not withinRadius((x,y), pastPoints, radius=max(h,w)):
            # pt1 = top left corner; pt2 = bottom right corner
            cv2.rectangle(img, pt1=(x,y), pt2=(x+w, y+h),
                          color=(0,0,255,255), thickness=2)
            matches.append((x + w//2, y + h//2))
            pastPoints.append((x,y))

    return matches, npToQpixmap(template), npToQpixmap(img)
