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


def activation(self):
    try:
        self.window.start_button_4.setEnabled(False)
        session = Browser(dir_path=self.window.driver_path)

        path = self.window.path_input_4.text()
        sheetname = self.window.sheet_input_4.text()
        id = self.window.id_input_4.text()
        date = self.window.date_input_4.text()
        timer = self.window.time_input_4.text()
        if '' in (path, sheetname, id, date, timer):
            self.output_signal.emit('Заполните все поля', self.window.output_4)
            self.window.start_button_4.setEnabled(True)
            return
        dates = activate_excel(self, path, sheetname, id, date, timer)

        if not preload(self, self.window.output_4, session):
            self.output_signal.emit('Процесс остановлен', self.window.output_4)
            self.window.start_button_4.setEnabled(True)
            return

        self.output_signal.emit('Активация запущена', self.window.output_4)
        self.stop.setEnabled(True)

        del_data = []
        del_keys = []
        replace_keys = []
        while dates:
            for key in dates.keys():
                if self.stop_flag:
                    raise Exception('Активация остановлена')
                if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                    for data in dates[key]:
                        status = activate(self.window, session, data)
                        if status == 0:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Не найден', self.window.output_4)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Не найден')
                        elif status == 1:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Объявление активировано', self.window.output_4)
                            self.window.report(data[0] + ' - Объявление активировано')
                        elif status == 2:
                            replace_keys.append(key)
                            self.output_signal.emit(data[0] + ' - Активация перенесена на 2 минуты', self.window.output_4)
                        else:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Объявление не активировано, ошибка', self.window.output_4)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Объявление не активировано, ошибка')
                            self.window.report(status, 'Активация')
                    for data in del_data:
                        dates[key].remove(data)
                    if not dates[key]:
                        del_keys.append(key)
            for key in replace_keys:
                new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                if new_key in dates:
                    for lst in dates.pop(key):
                        dates[new_key].append(lst)
                else:
                    dates[new_key] = dates.pop(key)
            for key in del_keys:
                dates.pop(key)
            del_data.clear()
            del_keys.clear()
            replace_keys.clear()
        self.stop.setEnabled(False)
        session.exit()
        self.output_signal.emit('Активация выполненна', self.window.output_4)
        self.window.start_button_4.setEnabled(True)
    except Exception as e:
        self.stop.setEnabled(False)
        session.exit()
        if not self.stop_flag:
            self.window.report(str(e), 'Активация')
            self.output_signal.emit('Активация остановлена, ошибка', self.window.output_4)
            self.window.report('Активация остановлена, ошибка')
        self.window.start_button_4.setEnabled(True)


def activate(window, session, data):
    try:
        link = 'https://www.olx.ua/d/myaccount/finished?query=' + data[0]
        session.browser.get(link)
        if session.wait('//button[@data-cy="welcome-modal-accept"]', timer=10):
            time.sleep(1)
            session.browser.find_element_by_xpath('//button[@data-cy="welcome-modal-accept"]').click()
        if session.wait('//button[@aria-label="Close"]', timer=10):
            time.sleep(1)
            session.browser.find_element_by_xpath('//button[@aria-label="Close"]').click()
        if session.wait('//button[@data-cy="ads-reposting-dismiss"]', timer=10):
            time.sleep(1)
            session.browser.find_element_by_xpath('//button[@data-cy="ads-reposting-dismiss"]').click()
        if not session.wait('//button[@aria-label="Активировать"]'):
            if not session.wait('//div[@class="userbox-dd__user-name"]'):
                if relogin(window, session):
                    session.browser.get(link)
                    if session.wait('//button[@aria-label="Активировать"]'):
                        session.browser.find_element_by_xpath('//button[@aria-label="Активировать"]').click()
                        time.sleep(5)
                        return 1
                else:
                    return 'Relogin Error'
            if data[1] < 5:
                data[1] += 1
                return 2
            else:
                return 0
        else:
            session.browser.find_element_by_xpath('//button[@aria-label="Активировать"]').click()
            time.sleep(5)
            return 1
    except Exception:
        return 0