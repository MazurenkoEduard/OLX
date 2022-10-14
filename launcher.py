# -*- coding: utf-8 -*-

import sys
import browser
from PyQt5 import QtWidgets
from form import config_create, Window


def main():
    config_create()
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    code = app.exec_()
    browser.clear()
    sys.exit(code)


if __name__ == '__main__':
    main()
