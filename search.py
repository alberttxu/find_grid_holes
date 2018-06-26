#!/usr/bin/env python3
import io
import numpy as np
import cv2
from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QBuffer


def QPixmapToPilRGB(qpixmap):
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    qpixmap.save(buf, "PNG")
    return Image.open(io.BytesIO(buf.data().data())).convert('RGBA')

def gaussianBlur(qpixmap):
    pilImg = QPixmapToPilRGB(qpixmap).filter(ImageFilter.GaussianBlur)
    return QPixmap.fromImage(ImageQt(pilImg))

# prevent including the same hole multiple times
def nearby_points(pt, radius=10):
    x, y = pt
    s = set()
    for i in range(radius):
        for j in range(radius):
            s.add((x+i, y+j))
            s.add((x+i, y-j))
            s.add((x-i, y+j))
            s.add((x-i, y-j))
    return s

# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def find_holes(qpixImg, qpixTemplate, threshold=0.8,
               blur_template=False, blur_img=False):
    """returns QPixmap with green square around matches"""
    img = QPixmapToPilRGB(qpixImg)
    template = QPixmapToPilRGB(qpixTemplate)

    if blur_img:
        img = img.filter(ImageFilter.GaussianBlur)
    img = np.array(img)
    if blur_template:
        template = template.filter(ImageFilter.GaussianBlur)
    template = np.array(template)

    h, w, _ = template.shape
    correlation_scores = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(correlation_scores >= threshold)

    hole_coordinates = []
    past_points = set()
    for pt in zip(*loc[::-1]):
        if pt not in past_points:
            # pt1 = top left corner; pt2 = bottom right corner
            cv2.rectangle(img, pt1=pt, pt2=(pt[0]+w, pt[1]+h),
                          color=(0,0,255,255), thickness=2)
            hole_coordinates.append((pt[0] + w//2, pt[1] + h//2))
            past_points.update(nearby_points(pt, radius=(int(max(h,w)/3))))

    return (hole_coordinates,
            QPixmap.fromImage(ImageQt(Image.fromarray(template))),
            QPixmap.fromImage(ImageQt(Image.fromarray(img))))

