# -*- coding: utf-8 -*-

import os
import telebot
from playsound import playsound
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.Qt import QSettings
import design
import warnings

from utils import login
from operations.advertise import advertise
from operations.statistics import stats
from operations.raises import raises
from operations.activate import activation

warnings.filterwarnings("ignore")

CURRENT_VERSION = ['0', '8', '3']

TOKEN = "1627942449:AAGKtgQSz4lznPbPiS9VFmm3-zR6KUr_rNY"
bot = telebot.TeleBot(TOKEN)


class Thread(QThread):
    bar_signal = pyqtSignal(int, QtWidgets.QProgressBar)
    output_signal = pyqtSignal(str, QtWidgets.QTextBrowser)

    def __init__(self, window, func, stop=None, login=False):
        super().__init__()
        self.window = window
        self.func = func
        self.login = login
        self.stop = stop
        self.stop_flag = False

    def run(self):
        if self.login:
            self.func(self)
        else:
            if self.window.check_log():
                try:
                    self.func(self)
                except Exception as e:
                    self.window.report(str(e), 'Run Thread')
                self.stop_flag = False
            else:
                self.window.login_output.append('Перезайдите в аккаунт')

    def stop_thread(self):
        self.stop.setEnabled(False)
        self.stop_flag = True


class Window(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # Cookies
        self.cookies_location = 'data\\cookies.txt'
        # Browsers
        self.driver_path = 'data\\driver\\'
        # Browse Button
        self.path_button_1.clicked.connect(lambda: self.browse_folder(self.path_input_1))
        self.path_button_2.clicked.connect(lambda: self.browse_folder(self.path_input_2))
        self.path_button_3.clicked.connect(lambda: self.browse_folder(self.path_input_3))
        self.path_button_4.clicked.connect(lambda: self.browse_folder(self.path_input_4))
        # Login
        self.login = Thread(window=self, func=login, login=True)
        self.login.output_signal.connect(self.output_signal_accept)
        self.login_button.clicked.connect(self.login.start)
        # Start
        self.start1 = Thread(window=self, func=advertise, stop=self.stop_button_1)
        self.start1.output_signal.connect(self.output_signal_accept)

        self.start2 = Thread(window=self, func=stats, stop=self.stop_button_2)
        self.start2.output_signal.connect(self.output_signal_accept)
        self.start2.bar_signal.connect(self.bar_signal_accept)

        self.start3 = Thread(window=self, func=raises, stop=self.stop_button_3)
        self.start3.output_signal.connect(self.output_signal_accept)
        self.start3.bar_signal.connect(self.bar_signal_accept)

        self.start4 = Thread(window=self, func=activation, stop=self.stop_button_4)
        self.start4.output_signal.connect(self.output_signal_accept)

        self.start_button_1.clicked.connect(self.start1.start)
        self.start_button_2.clicked.connect(self.start2.start)
        self.start_button_3.clicked.connect(self.start3.start)
        self.start_button_4.clicked.connect(self.start4.start)
        # Stop
        self.stop_button_1.clicked.connect(self.start1.stop_thread)
        self.stop_button_2.clicked.connect(self.start2.stop_thread)
        self.stop_button_3.clicked.connect(self.start3.stop_thread)
        self.stop_button_4.clicked.connect(self.start4.stop_thread)
        # Settings
        self.settings_button.clicked.connect(self.settings)
        # User Id
        self.user_id_input.textChanged.connect(self.id_change)
        # LogInfo
        self.login_text = ''
        self.pass_text = ''
        self.login_input.textChanged.connect(self.login_change)
        self.password_input.textChanged.connect(self.pass_change)
        # Telegram ID
        self.CreatorID = '478373716'
        self.UserID = None
        # Version
        self.version.setText('.'.join(CURRENT_VERSION))

        self.load_settings()

    @staticmethod
    def bar_signal_accept(value, bar):
        if value >= 100:
            bar.setValue(100)
        else:
            bar.setValue(value)

    @staticmethod
    def output_signal_accept(text, output):
        output.append(text)

    def browse_folder(self, input):
        settings = QSettings('data\\input_data.ini', QSettings.IniFormat)
        path = settings.value("dir_path")
        if not path:
            path = os.environ['USERPROFILE'] + '\\Desktop'
        directory = QtWidgets.QFileDialog.getOpenFileName(self, 'Excel File', path, 'Excel file (*.xlsx *.xls)')[0]
        if directory:
            settings.setValue('dir_path', directory)
            input.setText(directory.replace('/', '\\'))

    def check_log(self):
        with open(self.cookies_location, 'rb') as file:
            status = file.read()
        if not status:
            return False
        return True

    def settings(self):
        if self.dockWidget.isVisible():
            self.dockWidget.hide()
        else:
            self.dockWidget.show()

    def id_change(self):
        self.UserID = self.user_id_input.text()

    def login_change(self):
        self.login_text = self.login_input.text()

    def pass_change(self):
        self.pass_text = self.password_input.text()

    def report(self, error, section=None, image=None):
        try:
            if section:
                mess = section + '\n' + error
                if image:
                    with open(f'data/{image}', 'rb') as file:
                        img = file.read()
                    bot.send_photo(self.CreatorID, img, caption=mess)
                else:
                    bot.send_message(self.CreatorID, text=mess)
            elif self.UserID:
                mess = error
                bot.send_message(self.UserID, mess)
        except Exception as e:
            mess = 'Report function error' + '\n' + str(e)
            bot.send_message(self.CreatorID, mess)

    def audio(self, path):
        try:
            if self.sound_button.isChecked():
                sounds = os.listdir('data\\sounds')
                for s in sounds:
                    if s.find(path) != -1:
                        playsound('data\\sounds\\' + s, False)
                        break
        except Exception as e:
            self.report(str(e), 'Звук')

    def save_settings(self):
        try:
            settings = QSettings('data\\input_data.ini', QSettings.IniFormat)
            settings.setValue('sheet1', self.sheet_input_1.text())
            settings.setValue('sheet2', self.sheet_input_2.text())
            settings.setValue('sheet3', self.sheet_input_3.text())
            settings.setValue('sheet4', self.sheet_input_4.text())
            settings.setValue('id1', self.id_input_1.text())
            settings.setValue('id2', self.id_input_2.text())
            settings.setValue('id3', self.id_input_3.text())
            settings.setValue('id4', self.id_input_4.text())
            settings.setValue('path1', self.path_input_1.text())
            settings.setValue('path2', self.path_input_2.text())
            settings.setValue('path3', self.path_input_3.text())
            settings.setValue('path4', self.path_input_4.text())
            settings.setValue('date1', self.date_input_1.text())
            settings.setValue('date4', self.date_input_4.text())
            settings.setValue('time1', self.time_input_1.text())
            settings.setValue('time4', self.time_input_4.text())
            settings.setValue('tariff1', self.tariff_input_1.text())
            settings.setValue('addit1', self.addit_input_1.text())
            settings.setValue('user_id', self.user_id_input.text())
            settings.setValue('login', self.login_input.text())
            settings.setValue('password', self.password_input.text())
            if self.sound_button.isChecked():
                settings.setValue('sound', '1')
            else:
                settings.setValue('sound', '0')
        except Exception:
            pass

    def load_settings(self):
        try:
            settings = QSettings('data\\input_data.ini', QSettings.IniFormat)
            self.sheet_input_1.setText(settings.value('sheet1') if settings.value('sheet1') else "Лист1")
            self.sheet_input_2.setText(settings.value('sheet2') if settings.value('sheet2') else "Лист1")
            self.sheet_input_3.setText(settings.value('sheet3') if settings.value('sheet3') else "Лист1")
            self.sheet_input_4.setText(settings.value('sheet4') if settings.value('sheet4') else "Лист1")
            self.id_input_1.setText(settings.value('id1') if settings.value('id1') else "Id")
            self.id_input_2.setText(settings.value('id2') if settings.value('id2') else "Id")
            self.id_input_3.setText(settings.value('id3') if settings.value('id3') else "Id")
            self.id_input_4.setText(settings.value('id4') if settings.value('id4') else "Id")
            self.path_input_1.setText(settings.value('path1'))
            self.path_input_2.setText(settings.value('path2'))
            self.path_input_3.setText(settings.value('path3'))
            self.path_input_4.setText(settings.value('path4'))
            self.date_input_1.setText(settings.value('date1') if settings.value('date1') else "Date")
            self.date_input_4.setText(settings.value('date4') if settings.value('date4') else "Date")
            self.time_input_1.setText(settings.value('time1') if settings.value('time1') else "Time")
            self.time_input_4.setText(settings.value('time4') if settings.value('time4') else "Time")
            self.tariff_input_1.setText(settings.value('tariff1') if settings.value('tariff1') else "Tariff1")
            self.addit_input_1.setText(settings.value('addit1') if settings.value('addit1') else "Tariff2")
            self.user_id_input.setText(settings.value('user_id'))
            self.login_input.setText(settings.value('login'))
            self.login_text = self.login_input.text()
            self.password_input.setText(settings.value('password'))
            self.pass_text = self.password_input.text()
            self.sound_button.setChecked(bool(int(settings.value('sound'))))
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_settings()


def config_create():
    if not os.path.exists('data'):
        os.mkdir('data')
    if not os.path.exists('data\\driver'):
        os.mkdir('data\\driver')
    if not os.path.exists('data\\sounds'):
        os.mkdir('data\\sounds')
    if not os.path.exists('data\\cookies.txt'):
        file = open('data\\cookies.txt', 'w')
        file.close()
