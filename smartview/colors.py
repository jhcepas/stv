import colorsys
import random

def random_color(h=None, l=None, s=None, num=None, sep=None, seed=None):
    """ returns the RGB code of a random color. Hue (h), Lightness (l)
    and Saturation (s) of the generated color could be fixed using the
    pertinent function argument.  """
    def rgb2hex(rgb):
        return '#%02x%02x%02x' % rgb
    def hls2hex(h, l, s):
        return rgb2hex( tuple([int(x*255) for x in colorsys.hls_to_rgb(h, l, s)]))

    if not h:
        if seed:
            random.seed(seed)
        color = 1.0 / random.randint(1, 360)
        print(color)
    else:
        color = h

    if not num:
        n = 1
        sep = 1
    if not sep:
        n = num
        sep = (1.0/n)

    evenly_separated_colors =  [color + (sep*n) for n in range(n)]

    rcolors = []
    for h in evenly_separated_colors:
        if not s:
            s = 0.5
        if not l:
            l = 0.5
        rcolors.append(hls2hex(h, l, s))
    if num:
        return rcolors
    else:
        return rcolors[0]
