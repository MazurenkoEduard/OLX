# -*- coding: utf-8 -*-

import pandas as pd
from selenium.webdriver.common.by import By
from operations import Operation


class Raise(Operation):
    def raise_excel(self, path, sheetname, id):
        excel_data_df = pd.read_excel(path, sheet_name=sheetname, converters={id: str})
        ids = excel_data_df[id].tolist()
        return ids
    
    def raises(self):
        try:
            path = self.window.path_input_3.text()
            sheetname = self.window.sheet_input_3.text()
            id = self.window.id_input_3.text()
            if '' in (path, sheetname, id):
                self.thread.output_signal.emit('Заполните все поля', self.window.output_3)
                self.window.start_button_3.setEnabled(True)
                return None
            ids = self.raise_excel(path, sheetname, id)
            if not ids:
                return None

            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.window.output_3)
                return None
    
            self.thread.output_signal.emit('Процесс начался, ожидайте', self.window.output_3)
            self.thread.bar_signal.emit(0, self.window.up_bar)
            self.window.up_bar.show()
    
            tariff = []
            date = []
            timer = []
            dates = []
            times = []
            long = 15
    
            for i in range(long):
                dates.append([])
                times.append([])
            for i in range(len(ids)):
                self.session.browser.get("https://www.olx.ua/myaccount/pro/?query=" + ids[i])
                if i == 0:
                    self.hide_popup()
                toggle_button = self.session.wait('//div[@data-testid="flyout-toggle"]/button', timer=10)
                if toggle_button:
                    toggle_button.click()
                else:
                    tariff.append('')
                    date.append('')
                    timer.append('')
                    for l in range(long):
                        dates[l].append('')
                        times[l].append('')
                    self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)
                    self.thread.output_signal.emit(ids[i] + ' - Объявление не рекламируется', self.window.output_3)
                    continue
                if self.session.wait('//div[@data-testid="flyout-content"]'):
                    divs = len(self.session.browser.find_elements(By.XPATH, '//div[@data-testid="flyout-content"]/div/div'))
                    if divs > 1:
                        try:
                            index = 3
                            tariff_text = self.session.browser.find_element(
                                By.XPATH, '//div[@data-testid="flyout-content"]/div/div[1]/p[1]').text
                            tariff_time = self.session.browser.find_element(
                                By.XPATH, '//div[@data-testid="flyout-content"]/div/div[1]/p[2]').text.split(': ')[1].split(', ')
                            tariff.append(tariff_text)
                            date.append(tariff_time[0])
                            timer.append(tariff_time[1])
                        except:
                            index = 0
                            tariff.append('')
                            date.append('')
                            timer.append('')
                            for l in range(long):
                                dates[l].append('')
                                times[l].append('')
                    else:
                        index = 1
                        tariff.append('')
                        date.append('')
                        timer.append('')
                    if index == 0:
                        self.thread.output_signal.emit(ids[i] + ' - Ошибка', self.window.output_3)
                    elif self.session.browser.find_element(
                            By.XPATH, f'//div[@data-testid="flyout-content"]/div/div[{index}]/p').text == 'Поднятие вверх списка':
                        table = self.session.browser.find_elements(
                            By.XPATH, f'//div[@data-testid="flyout-content"]/div/div[{index}]/div/p')
                        dateX = []
                        timeX = []
                        for t in table:
                            text = t.text.split(', ')
                            dateX.append(text[0])
                            timeX.append(text[1])
                        for rng in range(len(dateX)):
                            dates[rng].append(dateX[rng])
                            times[rng].append(timeX[rng])
                        for l in range(len(dateX), long):
                            dates[l].append('')
                            times[l].append('')
                    else:
                        for l in range(long):
                            dates[l].append('')
                            times[l].append('')
                else:
                    tariff.append('')
                    date.append('')
                    timer.append('')
                    for l in range(long):
                        dates[l].append('')
                        times[l].append('')
                    self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)
                    self.thread.output_signal.emit(ids[i] + ' - Объявление не рекламируется', self.window.output_3)
                    continue
                self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)
    
            data = {'Id': ids,
                    'Тариф': tariff,
                    'Действует до': date,
                    'Время': timer}
            for i in range(long):
                while len(dates[i]) < len(ids):
                    dates[i].append('')
                    times[i].append('')
            for i in range(long):
                data['Дата' + str(i + 1)] = dates[i]
                data['Время' + str(i + 1)] = times[i]
            self.write_excel(data, path, sheetname)
            self.thread.output_signal.emit('Данные получены', self.window.output_3)
        except Exception as e:
            self.window.report(str(e), 'Поднятия')
            self.thread.output_signal.emit(str(e), self.window.output_3)
        finally:
            self.session.exit()
            self.window.up_bar.hide()
