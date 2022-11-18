# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from browser import Browser
from utils import preload, relogin


def activate_excel(self, path, sheetname, id, date, timer):
    data = pd.read_excel(path, sheet_name=sheetname)
    ids = data[id].tolist()
    for i in range(len(ids)):
        if pd.isnull(ids[i]):
            ids[i] = ''
        else:
            ids[i] = str(ids[i])
    dates = data[date].tolist()
    for i in range(len(dates)):
        if pd.isnull(dates[i]):
            dates[i] = ''
        else:
            dates[i] = dates[i].strftime("%Y.%m.%d")
    times = data[timer].tolist()
    for i in range(len(times)):
        if pd.isnull(times[i]):
            times[i] = ''
        else:
            times[i] = times[i].strftime("%H:%M")
    result = {dates[i] + ' ' + times[i]: [] for i in range(len(ids))}
    today = time.strftime("%Y.%m.%d", time.localtime())
    for i in range(len(ids)):
        if not (ids[i] and dates[i] and times[i]):
            self.output_signal.emit(ids[i] + ' - Заполните все столбцы', self.window.output_4)
        elif dates[i] < today:
            self.output_signal.emit(ids[i] + ' - Реклама не активированна, опоздание по времени', self.window.output_4)
        elif dates[i] > today:
            result[dates[i] + ' ' + times[i]].append([ids[i], 0])
        elif dates[i] == today:
            if datetime.strptime(datetime.now().strftime('%H:%M'), '%H:%M') <= datetime.strptime(times[i], '%H:%M'):
                result[dates[i] + ' ' + times[i]].append([ids[i], 0])
            else:
                self.output_signal.emit(ids[i] + ' - Реклама не активированна, опоздание по времени', self.window.output_4)

    return {k: v for k, v in result.items() if v}


def get_dates(self):
    path = self.window.path_input_4.text()
    sheetname = self.window.sheet_input_4.text()
    id = self.window.id_input_4.text()
    date = self.window.date_input_4.text()
    timer = self.window.time_input_4.text()
    if '' in (path, sheetname, id, date, timer):
        self.output_signal.emit('Заполните все поля', self.window.output_4)
        self.window.start_button_4.setEnabled(True)
        return None
    return activate_excel(self, path, sheetname, id, date, timer)


def activation(self):
    self.window.start_button_4.setEnabled(False)
    session = Browser(dir_path=self.window.driver_path)
    try:
        dates = get_dates(self)
        if not dates:
            return None

        if not preload(self, self.window.output_4, session):
            self.output_signal.emit('Процесс остановлен', self.window.output_4)
            self.window.start_button_4.setEnabled(True)
            return None

        self.output_signal.emit('Активация запущена', self.window.output_4)
        self.stop.setEnabled(True)

        while dates:
            for key in list(dates.keys()).copy():
                if self.stop_flag:
                    raise Exception('Активация остановлена')
                if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                    for data in dates[key].copy():
                        status = activate(self.window, session, data)
                        if status == 100:
                            dates[key].remove(data)
                            self.output_signal.emit(data[0] + ' - Объявление активировано', self.window.output_4)
                            self.window.report(data[0] + ' - Объявление активировано')
                        elif status == 200:
                            new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                            if new_key in dates:
                                for lst in dates.pop(key):
                                    dates[new_key].append(lst)
                            else:
                                dates[new_key] = dates.pop(key)
                            self.output_signal.emit(data[0] + ' - Активация перенесена на 2 минуты', self.window.output_4)
                        elif status == 400:
                            dates[key].remove(data)
                            self.output_signal.emit(data[0] + ' - Не найден', self.window.output_4)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Не найден')
                        else:
                            dates[key].remove(data)
                            self.output_signal.emit(data[0] + ' - Объявление не активировано, ошибка', self.window.output_4)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Объявление не активировано, ошибка')
                            self.window.report(status, 'Активация')
                    if not dates[key]:
                        dates.pop(key)
        self.output_signal.emit('Активация выполненна', self.window.output_4)
    except Exception as e:
        if not self.stop_flag:
            self.window.report(str(e), 'Активация')
            self.output_signal.emit('Активация остановлена, ошибка', self.window.output_4)
            self.window.report('Активация остановлена, ошибка')
    finally:
        self.stop.setEnabled(False)
        session.exit()
        self.window.start_button_4.setEnabled(True)


def activate(window, session, data):
    try:
        link = 'https://www.olx.ua/d/myaccount/finished?query=' + data[0]
        session.browser.get(link)
        accept_button = session.wait('//button[@data-cy="welcome-modal-accept"]', timer=10)
        if accept_button:
            time.sleep(1)
            accept_button.click()
        close_button = session.wait('//button[@aria-label="Close"]', timer=10)
        if close_button:
            time.sleep(1)
            close_button.click()
        dismiss_button = session.wait('//button[@data-cy="ads-reposting-dismiss"]', timer=10)
        if dismiss_button:
            time.sleep(1)
            dismiss_button.click()
        activate_button = session.wait('//button[@aria-label="Активировать"]')
        if activate_button:
            activate_button.click()
            time.sleep(5)
            return 100
        else:
            if not session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                path2='//div[@class="userbox-dd__user-name"]'):
                if relogin(window, session):
                    session.browser.get(link)
                    activate_button = session.wait('//button[@aria-label="Активировать"]')
                    if activate_button:
                        activate_button.click()
                        time.sleep(5)
                        return 100
                else:
                    return 'Relogin Error'
            if data[1] < 5:
                data[1] += 1
                return 200
            else:
                return 400
    except Exception as e:
        return str(e)
