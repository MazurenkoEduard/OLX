# -*- coding: utf-8 -*-

import sys
from browser import Browser
from PyQt5 import QtWidgets
from form import config_create, Window


def main():
    config_create()
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    code = app.exec_()
    Browser.clear()
    sys.exit(code)


if __name__ == '__main__':
    main()
