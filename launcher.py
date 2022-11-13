# -*- coding: utf-8 -*-

import os
import sys
from browser import Browser
from PyQt5 import QtWidgets
from form import Window


def make_dir():
    if not os.path.exists('data'):
        os.mkdir('data')
    if not os.path.exists('data\\driver'):
        os.mkdir('data\\driver')
    if not os.path.exists('data\\sounds'):
        os.mkdir('data\\sounds')
    if not os.path.exists('data\\cookies.txt'):
        file = open('data\\cookies.txt', 'w')
        file.close()


def main():
    make_dir()
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    code = app.exec_()
    Browser.clear()
    sys.exit(code)


if __name__ == '__main__':
    main()
