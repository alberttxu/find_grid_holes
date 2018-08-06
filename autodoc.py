#!/usr/bin/env python3
from search import makeGroupsOfPoints, closestPtToCentroid

class NavFilePoint:

    def __init__(self, label: str, regis: int, ptsX: int, ptsY: int,
            zHeight: float, drawnID: int, numPts: int = 1, itemType: int = 0,
            color: int = 0, groupID: int = 0, **kwargs):
        self._label = label
        self.Color = color
        self.NumPts = numPts
        self.Regis = regis
        self.Type = itemType
        self.PtsX = ptsX
        self.PtsY = ptsY
        self.DrawnID = drawnID
        self.GroupID = groupID
        self.CoordsInMap = [ptsX, ptsY, zHeight]
        vars(self).update(kwargs)

    def toString(self):
        result = [f"[Item = {self._label}]"]
        for key, val in vars(self).items():
            if key == '_label': continue
            if key == 'CoordsInMap':
                val = ' '.join(str(x) for x in val)
            result.append(f"{key} = {val}")
        result.append('\n')
        return '\n'.join(result)


def isValidAutodoc(navfile):
    with open(navfile) as f:
        for line in f:
            if line.strip():
                if line.split()[0] == 'AdocVersion':
                    print(line)
                    return True
                else:
                    print("error: could not find AdocVersion")
                    return False

def isValidLabel(data: 'list', label: str):
    try:
        mapSectionIndex = data.index(f"[Item = {label}]")
    except:
        print("unable to write new autodoc file: label not found")
        return False
    return True

def sectionAsDict(data: 'list', label: str):
    start = data.index(f"[Item = {label}]") + 1
    section = data[start : data.index('', start)]

    result = {}
    for line in section:
        key, val = [s.strip() for s in line.split('=')]
        if key != 'Note':
            val = val.split()
        result[key] = val
    return result

def coordsToNavPoints(coords, mapSection: 'Dict', startLabel, groupPoints,
                                                              groupRadius):
    regis = int(mapSection['Regis'][0])
    drawnID = int(mapSection['MapID'][0])
    zHeight = float(mapSection['StageXYZ'][2])

    navPoints = []
    label = startLabel
    if groupPoints:
        for group in makeGroupsOfPoints(coords, groupRadius):
            groupID = id(group)
            groupLeader = closestPtToCentroid(group)
            group = [groupLeader] + [pt for pt in group if pt != groupLeader]
            for pt in group:
                navPoints.append(NavFilePoint(label, regis, *pt, zHeight,
                                              drawnID, groupID=groupID))
                label += 1
    else:
        for pt in self.coords:
            navPoints.append(NavFilePoint(label, regis, *pt, zHeight, drawnID))
            label += 1
    return navPoints

