import numpy as np
facegrid = np.array(
    [
    [None, 0, 1, 10, 20],
    [None, 0, 1, 10, 20],
    [None, 0, 1, 10, 20],
    [None, 1, 1, 11, 10],
    [None, 1, 1, 11, 15],
    [None, 2, 1, 10, 30],]
)

print facegrid.find_objects()
rows = facegrid[:,1]==0


print rows

