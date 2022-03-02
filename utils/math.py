import math


def round_js(value):
    x = math.floor(value)
    if (value - x) < 0.5:
        return x
    else:
        return math.ceil(value)
