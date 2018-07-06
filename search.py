#!/usr/bin/env python3
import numpy as np
import cv2

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

def drawCross(img: 'ndarray', x, y):
    blue = (0,0,255,255)
    cv2.line(img, (x-5,y), (x+5,y), blue, 2)
    cv2.line(img, (x,y-5), (x,y+5), blue, 2)


# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def find_holes(img: 'ndarray', template: 'ndarray', threshold=0.8):
    """returns match coords list and ndarray with blue cross at matches"""
    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)
    # write back to img
    matches = []
    for x, y, _ in scoresIndex:
        if not withinRadius((x,y), matches, radius=max(h,w)):
            x += w//2
            y += h//2
            drawCross(img, x, y)
            matches.append((x,y))
    return matches, img
