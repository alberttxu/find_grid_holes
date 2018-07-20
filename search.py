#!/usr/bin/env python3
import numpy as np
import cv2

# prevent including the same hole multiple times
def withinRadius(x, y, coords, radius):
    radius_2 = radius ** 2
    if len(coords) == 0:
        return False
    for c in coords:
        distance_2 = (c[0]-x)**2 + (c[1]-y)**2
        if distance_2 < radius_2:
            return True
    return False

def drawCross(img: 'ndarray', x, y):
    blue = (0,0,255,255)
    cv2.line(img, (x-5,y), (x+5,y), blue, 2)
    cv2.line(img, (x,y-5), (x,y+5), blue, 2)

# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def find_holes(img: 'ndarray', template: 'ndarray', threshold=0.8):
    """Returns coordinate list of positions with the highest cross-correlation
    to the template array and also returns the same input array with blue
    crosses at each coordinate.

    0,0 is at the bottom-left corner, with +y going up and +x going right.
    """

    img = np.flip(img, 0).copy()
    template = np.flip(template, 0).copy()
    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)
    # write back to img
    matches = []
    for x, y, _ in scoresIndex:
        if not withinRadius(x, y, matches, radius=max(h,w)):
            x += w//2
            y += h//2
            drawCross(img, x, y)
            matches.append((x,y))
    return matches, img
