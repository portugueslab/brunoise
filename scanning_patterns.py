import numpy as np
from numba import jit

@jit(nopython=True)
def make_arc(cx, cy, radius, n_segments=12, is_left=True):
    """
    Make an half-circle arc with the centre cx, cy with n_segments points,
    """
    angles = np.linspace((3*np.pi/2 if is_left else -np.pi/2), np.pi/2, n_segments)
    return np.cos(angles)*radius+cx, np.sin(angles)*radius+cy


@jit(nopython=True)
def simple_scanning_pattern(n_x, n_y, n_turn, pause_x=False):
    """
    n_x valid x resolution
    n_y valid y resoultion
    n_turn number of pixels outside of scanning area
    pause_x = whether the x-line scanning pauses at the end
    """
    points_x = []
    points_y = []
    for i_y in range(n_y):
        first_line = i_y == 0
        last_line = i_y == n_y-1
        if i_y % 2 == 0:
            path_x = range(0 if first_line else -n_turn,
                           n_x+1 if last_line else n_x+n_turn+(1 if pause_x else 0))
        else:
            path_x = range(n_x+n_turn,
                           -1 if last_line else -n_turn - (1 if pause_x else 0), -1)
        points_x.extend(path_x)
        points_y.extend([i_y for _ in range(len(path_x))])
    return np.array(points_x), np.array(points_y)
