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
        color = random.randint(1, 99)/100.
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





aafgcolors = {
    'A':"#000000" ,
    'R':"#000000" ,
    'N':"#000000" ,
    'D':"#000000" ,
    'C':"#000000" ,
    'Q':"#000000" ,
    'E':"#000000" ,
    'G':"#000000" ,
    'H':"#000000" ,
    'I':"#000000" ,
    'L':"#000000" ,
    'K':"#000000" ,
    'M':"#000000" ,
    'F':"#000000" ,
    'P':"#000000" ,
    'S':"#000000" ,
    'T':"#000000" ,
    'W':"#000000" ,
    'Y':"#000000" ,
    'V':"#000000" ,
    'B':"#000000" ,
    'Z':"#000000" ,
    'X':"#000000",
    '.':"#000000",
    '-':"#000000",
}

aabgcolors = {
    'A':"#C8C8C8" ,
    'R':"#145AFF" ,
    'N':"#00DCDC" ,
    'D':"#E60A0A" ,
    'C':"#E6E600" ,
    'Q':"#00DCDC" ,
    'E':"#E60A0A" ,
    'G':"#EBEBEB" ,
    'H':"#8282D2" ,
    'I':"#0F820F" ,
    'L':"#0F820F" ,
    'K':"#145AFF" ,
    'M':"#E6E600" ,
    'F':"#3232AA" ,
    'P':"#DC9682" ,
    'S':"#FA9600" ,
    'T':"#FA9600" ,
    'W':"#B45AB4" ,
    'Y':"#3232AA" ,
    'V':"#0F820F" ,
    'B':"#FF69B4" ,
    'Z':"#FF69B4" ,
    'X':"#BEA06E",
    '.':"#FFFFFF",
    '-':"#FFFFFF",
    }

ntfgcolors = {
    'A':'#000000',
    'G':'#000000',
    'I':'#000000',
    'C':'#000000',
    'T':'#000000',
    'U':'#000000',
    '.':"#000000",
    '-':"#000000",
    ' ':"#000000"
    }

ntbgcolors = {
    'A':'#A0A0FF',
    'G':'#FF7070',
    'I':'#80FFFF',
    'C':'#FF8C4B',
    'T':'#A0FFA0',
    'U':'#FF8080',
    '.':"#FFFFFF",
    '-':"#FFFFFF",
    ' ':"#FFFFFF"
}
