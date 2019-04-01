from PyQt4 import QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *
_QApp = QApplication(["ETE"])

symbol2size = {}

for ftype in ["Verdana", "Arial", "Sans Serif"]:
    for fstyle in [None, 'italic']:
        fm = QFontMetrics(QFont(ftype, pointSize=10))
        h = fm.height()
        symbol2size[(ftype, fstyle)] = [h, {}]
        width = symbol2size[(ftype, fstyle)][1]
        for letter in list("1234567890`~@#$%^&*()_-=+{}[]:'\",./?><;\\| abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            w = fm.width(letter)
            width[letter]=w
print symbol2size
