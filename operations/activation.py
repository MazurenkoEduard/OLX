# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from operations import Operation


class Activation(Operation):
    def activation_excel(self, path, sheetname, id, date, timer):
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
                self.thread.output_signal.emit(ids[i] + ' - Заполните все столбцы', self.output)
            elif dates[i] < today:
                self.thread.output_signal.emit(ids[i] + ' - Реклама не активированна, опоздание по времени', self.output)
            elif dates[i] > today:
                result[dates[i] + ' ' + times[i]].append([ids[i], 0])
            elif dates[i] == today:
                if datetime.strptime(datetime.now().strftime('%H:%M'), '%H:%M') <= datetime.strptime(times[i], '%H:%M'):
                    result[dates[i] + ' ' + times[i]].append([ids[i], 0])
                else:
                    self.thread.output_signal.emit(ids[i] + ' - Реклама не активированна, опоздание по времени', self.output)
    
        return {k: v for k, v in result.items() if v}
    
    def get_dates(self):
        path = self.window.path_input_4.text()
        sheetname = self.window.sheet_input_4.text()
        id = self.window.id_input_4.text()
        date = self.window.date_input_4.text()
        timer = self.window.time_input_4.text()
        if '' in (path, sheetname, id, date, timer):
            self.thread.output_signal.emit('Заполните все поля', self.output)
            self.window.start_button_4.setEnabled(True)
            return None
        return self.activation_excel(path, sheetname, id, date, timer)

    def activation(self):
        try:
            dates = self.get_dates()
            if not dates:
                return None
    
            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.output)
                return None
    
            self.thread.output_signal.emit('Активация запущена', self.output)
    
            while dates:
                for key in list(dates.keys()).copy():
                    if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                        for data in dates[key].copy():
                            status = self.activate(data)
                            if status == 100:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Объявление активировано', self.output)
                                self.window.report(data[0] + ' - Объявление активировано')
                            elif status == 200:
                                new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                                if new_key in dates:
                                    for lst in dates.pop(key):
                                        dates[new_key].append(lst)
                                else:
                                    dates[new_key] = dates.pop(key)
                                self.thread.output_signal.emit(data[0] + ' - Активация перенесена на 2 минуты', self.output)
                            elif status == 400:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Не найден', self.output)
                                self.window.audio('error')
                                self.window.report(data[0] + ' - Не найден')
                            else:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Объявление не активировано, ошибка', self.output)
                                self.window.audio('error')
                                self.window.report(data[0] + ' - Объявление не активировано, ошибка')
                                self.window.report(status, 'Activation')
                        if not dates[key]:
                            dates.pop(key)
            self.thread.output_signal.emit('Активация выполненна', self.output)
        except Exception as e:
            self.window.report(str(e), 'Activation')
            self.thread.output_signal.emit('Активация остановлена, ошибка', self.output)
            self.window.report('Активация остановлена, ошибка')
        finally:
            self.session.exit()

    def activate(self, data):
        try:
            link = 'https://www.olx.ua/d/myaccount/finished?query=' + data[0]
            self.session.browser.get(link)
            self.hide_popup()
            activate_button = self.session.wait('//button[@aria-label="Активировать"]', condition="click")
            if activate_button:
                activate_button.click()
                time.sleep(5)
                return 100
            else:
                if not self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                         path2='//div[@class="userbox-dd__user-name"]'):
                    if self.relogin():
                        self.session.browser.get(link)
                        activate_button = self.session.wait('//button[@aria-label="Активировать"]', condition="click")
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
