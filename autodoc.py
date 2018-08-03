#!/usr/bin/env python3

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

