#!/usr/bin/env python3
import numpy as np
import cv2


# for relative distance, square distance is faster to compute
def squareDist(pt1: 'tuple', pt2: 'tuple'):
    return (pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2

# prevent including the same hole multiple times
def pointsExistWithinRadius(center, coords, radius):
    radius_2 = radius ** 2
    if len(coords) == 0:
        return False
    for pt in coords:
        if squareDist(pt, center) < radius_2:
            return True
    return False

# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def templateMatch(img: 'ndarray', template: 'ndarray', threshold=0.8):
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

    matches = []
    for x, y, _ in scoresIndex:
        x += w//2
        y += h//2
        if not pointsExistWithinRadius((x,y), matches, radius=max(h,w)):
            matches.append((x,y))
    return matches

def centroid(pts: 'ndarray'):
    length = pts.shape[0]
    sum_x = np.sum(pts[:, 0])
    sum_y = np.sum(pts[:, 1])
    return sum_x/length, sum_y/length

def closestPtToCentroid(pts):
    """Returns the coordinate closest to the center of mass"""
    center = centroid(np.array(pts))
    closestPoint = pts[0]
    msd = squareDist(pts[0], center) # min square distance
    for pt in pts:
        dist_2 = squareDist(pt, center)
        if dist_2 < msd:
            closestPoint = pt
            msd = dist_2
    return closestPoint

def makeGroupsOfPoints(pts, max_radius):
    pts = [tuple(pt) for pt in sorted(pts, key=lambda pt: pt[0])]
    max_rad_2 = max_radius ** 2
    groups = []
    unprocessedPts = set(pts)
    while unprocessedPts:
        x = unprocessedPts.pop()
        group = [x]
        for pt in pts:
            if pt in unprocessedPts and squareDist(x, pt) < max_rad_2:
                group.append(pt)
                unprocessedPts.remove(pt)
        groups.append(group)
    return groups

