#!/usr/bin/env python3
import numpy as np
import cv2
from scipy.misc import imresize


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
def templateMatch(img: 'ndarray', templ: 'ndarray', threshold=0.8):
    """Returns coordinate list of positions with the highest cross-correlation
    to the template array and also returns the same input array with blue
    crosses at each coordinate. Images are internally downsampled 8x for faster
    computation.

    0,0 is at the bottom-left corner, with +y going up and +x going right.
    """

    # internally downsample image 8x for faster computation
    img = np.stack((imresize(img[:,:,i], 0.125) for i in range(4)), axis=2)
    templ = np.stack((imresize(templ[:,:,i], 0.125) for i in range(4)), axis=2)
    # flip both arrays upsidedown because of coordinate-axes
    img = np.flip(img, 0).copy()
    templ = np.flip(templ, 0).copy()
    h, w, *_ = templ.shape
    #print(h, w, _)
    xcorrScores = cv2.matchTemplate(img, templ, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)

    matches = []
    for x, y, _ in scoresIndex:
        x += w//2
        y += h//2
        if not pointsExistWithinRadius((x,y), matches, radius=max(h,w)):
            matches.append((x,y))
    # multiply back to get correct coordinates
    matches = [(8*x, 8*y) for x,y in matches]
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

def greedyPathThroughPts(coords):
    """Returns a list with the first item being the left most coordinate,
       and successive items being the minimum distance from the previous item.
    """
    coords = [tuple(pt) for pt in coords]
    leftMostPt = sorted(coords, key=lambda x: x[0])[0]
    unvisitedPts = set(coords)
    unvisitedPts.remove(leftMostPt)

    result = [leftMostPt]
    while unvisitedPts:
        closestPtToPrev = unvisitedPts.pop()
        unvisitedPts.add(closestPtToPrev)
        minDist = squareDist(closestPtToPrev, result[-1])
        for pt in unvisitedPts:
            distFromPrev = squareDist(pt, result[-1])
            if distFromPrev < minDist:
                minDist = distFromPrev
                closestPtToPrev = pt
        result.append(closestPtToPrev)
        unvisitedPts.remove(closestPtToPrev)
    return result
