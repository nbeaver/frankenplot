#
# frankenplot.data: functions for handling datasets
#

import matplotlib.numerix as nx

# ============================================================================

def getNumberUnique(vect):
    """
    Return the number of times elements appear in the vector 'vect' without
    repeating the first element of the vector.

    This only works for vectors like '[0, 1, 2, 3, 0, 1, 2, 3]'.
    """
    i = 1
    num = 0
    start = vect[0]
    max = vect.shape[0]
    while i < max:
        if vect[i] == start:
            break
        else:
            i += 1
    return i


def makeXYZ(xCol, yCol, zCol):
    idxs = nx.arange(0, zCol.shape[0], 1)
    nX = getNumberUnique(xCol)
    if nX == 1: # Y varies: (0, 0, z), (0, 1, z), ...
        nY = getNumberUnique(yCol)
        nX = int(nx.ceil(yCol.shape[0] / float(nY)))
        y = yCol[0:nY]
        x = getUniqueSequence(xCol, nX)
        z = nx.zeros((nY, nX), nx.Float)
        z[:, :] = nx.minimum.reduce(zCol)
        for i in range(0, nX):
            zc = zCol[nY*i:nY*(i+1)]
            n  = zc.shape[0]
            z[0:n,i] = zc
    else: # X varies: (0, 0, z), (1, 0, z), ...
        nY = int(nx.ceil(xCol.shape[0] / float(nX)))
        x = xCol[0:nX]
        y = getUniqueSequence(yCol, nY)
        z = nx.zeros((nY, nX), nx.Float)
        z[:, :] = nx.minimum.reduce(zCol)
        for i in range(0, nY):
            zc = zCol[nX*i:nX*(i+1)]
            n  = zc.shape[0]
            z[i, 0:n] = zc
    return x, y, z


def getUniqueSequence(vect, count):
    """Return a Numeric array containing the at most the first 'count' unique
    elements from the vector 'vect'.

    The 'vect' must contain at least one element.

    This only works for vectors like '[0, 0, 1, 1, 2, 2, 3, 3]'.
    """
    i = 0
    curr = None
    unique = []
    max = vect.shape[0]

    while i < max:
        if vect[i] == curr:
            i += 1
        else:
            if len(unique) == count:
                break
            else:
                curr = vect[i]
                unique.append(curr)
                i += 1

    return nx.array(unique)
