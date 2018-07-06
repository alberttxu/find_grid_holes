#!/usr/bin/env python3
import io
import numpy as np
import cv2
from PIL import Image, ImageFilter
from PIL.ImageQt import ImageQt
from PyQt5.QtGui import QPixmap, QImage
import cProfile, pstats, sys


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

#def drawCross(img: 'ndarray', x, y):


# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def find_holes(img: 'ndarray', template: 'ndarray', threshold=0.8):
    """returns QPixmap with green square around matches"""
    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)
    # write back to img
    matches = []
    pastPoints = []
    for x, y, _ in scoresIndex:
        if not withinRadius((x,y), pastPoints, radius=max(h,w)):
            # pt1 = top left corner; pt2 = bottom right corner
            cv2.rectangle(img, pt1=(x,y), pt2=(x+w, y+h),
                          color=(0,0,255,255), thickness=2)
            matches.append((x + w//2, y + h//2))
            pastPoints.append((x,y))
    return matches, img
