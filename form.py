# -*- coding: utf-8 -*-

import os
import telebot
from playsound import playsound
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.Qt import QSettings
import design
import warnings

from operations import Operation
from operations.advertise import Advertise
from operations.statistics import Statistic
from operations.raises import Raise
from operations.activate import Activate

from config import BOT_TOKEN, CREATOR_ID

warnings.filterwarnings("ignore")

CURRENT_VERSION = ['0', '9', '0']

bot = telebot.TeleBot(BOT_TOKEN)


class Thread(QObject):
    bar_signal = pyqtSignal(int, QtWidgets.QProgressBar)
    output_signal = pyqtSignal(str, QtWidgets.QTextBrowser)
    finished = pyqtSignal()

    def __init__(self, window):
        super(Thread, self).__init__()
        self.window = window

    def login(self):
        process = Operation(self, self.window, self.window.login_output, False)
        process.login()
        self.finished.emit()

    def advertise(self):
        process = Advertise(self, self.window, self.window.advertise_output)
        process.advertise()
        self.finished.emit()

    def statistics(self):
        process = Statistic(self, self.window, self.window.statistic_output)
        process.statistics()
        self.finished.emit()

    def raises(self):
        process = Raise(self, self.window, self.window.raise_output)
        process.raises()
        self.finished.emit()

    def activate(self):
        process = Activate(self, self.window, self.window.activate_output)
        process.activate()
        self.finished.emit()


class Window(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super(Window, self).__init__()
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
        self.create_thread(self.login_button)
        # Advertise
        self.create_thread(self.advertise_start, self.advertise_stop)
        # Statistic
        self.create_thread(self.statistic_start, self.statistic_stop)
        # Raise
        self.create_thread(self.raise_start, self.raise_stop)
        # Activate
        self.create_thread(self.activate_start, self.activate_stop)
        # Settings
        self.settings_button.clicked.connect(self.settings)
        # User Id
        self.user_id_input.textChanged.connect(self.id_change)
        # LogInfo
        self.login_text = ''
        self.pass_text = ''
        self.login_input.textChanged.connect(self.login_change)
        self.password_input.textChanged.connect(self.pass_change)
        # Telegram
        self.creator_id = CREATOR_ID
        self.user_id = None
        # Version
        self.version.setText('.'.join(CURRENT_VERSION))

        self.load_settings()

    def create_thread(self, start, stop=None):
        thread = QThread()
        operation = Thread(window=self)
        operation.moveToThread(thread)
        operation.output_signal.connect(self.output_signal_accept)
        operation.bar_signal.connect(self.bar_signal_accept)
        start.clicked.connect(thread.start)
        thread.started.connect(lambda: start.setEnabled(False))
        thread.started.connect(operation.advertise)
        operation.finished.connect(thread.quit)
        operation.finished.connect(operation.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: start.setEnabled(True))
        if stop:
            thread.started.connect(lambda: stop.setEnabled(True))
            stop.clicked.connect(lambda: stop.setEnabled(False))
            stop.clicked.connect(lambda: operation.finished.emit())
            thread.finished.connect(lambda: stop.setEnabled(False))

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
        self.user_id = self.user_id_input.text()

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
                    bot.send_photo(self.creator_id, img, caption=mess)
                else:
                    bot.send_message(self.creator_id, text=mess)
            elif self.user_id:
                mess = error
                bot.send_message(self.user_id, mess)
        except Exception as e:
            mess = 'Report function error' + '\n' + str(e)
            bot.send_message(self.creator_id, mess)

    def audio(self, path):
        try:
            if self.sound_button.isChecked():
                sounds = os.listdir('data\\sounds')
                for sound in sounds:
                    if sound.find(path) != -1:
                        playsound('data\\sounds\\' + sound, False)
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
            settings.setValue('service1', self.service_input_1.text())
            settings.setValue('user_id', self.user_id_input.text())
            settings.setValue('login', self.login_input.text())
            settings.setValue('password', self.password_input.text())
            if self.sound_button.isChecked():
                settings.setValue('sound', '1')
            else:
                settings.setValue('sound', '0')
        except Exception as e:
            self.report(str(e), 'Settings')

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
            self.tariff_input_1.setText(settings.value('tariff1') if settings.value('tariff1') else "Tariff")
            self.service_input_1.setText(settings.value('service1') if settings.value('service1') else "Service")
            self.user_id_input.setText(settings.value('user_id'))
            self.login_input.setText(settings.value('login'))
            self.login_text = self.login_input.text()
            self.password_input.setText(settings.value('password'))
            self.pass_text = self.password_input.text()
            self.sound_button.setChecked(bool(int(settings.value('sound'))))
        except Exception as e:
            self.report(str(e), 'Settings')
            
    def closeEvent(self, event):
        self.save_settings()
