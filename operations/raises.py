# -*- coding: utf-8 -*-

import time
import pandas as pd
from browser import Browser
from utils import preload, write_excel
from selenium.webdriver.common.by import By


def raise_excel(path, sheetname, id):
    excel_data_df = pd.read_excel(path, sheet_name=sheetname, converters={id: str})
    ids = excel_data_df[id].tolist()
    return ids


def raises(self):
    self.window.start_button_3.setEnabled(False)
    session = Browser(dir_path=self.window.driver_path)
    try:
        path = self.window.path_input_3.text()
        sheetname = self.window.sheet_input_3.text()
        id = self.window.id_input_3.text()
        if '' in (path, sheetname, id):
            self.output_signal.emit('Заполните все поля', self.window.output_3)
            self.window.start_button_3.setEnabled(True)
            return None
        ids = raise_excel(path, sheetname, id)
        if not ids:
            return None

        if not preload(self, self.window.output_3, session):
            self.output_signal.emit('Процесс остановлен', self.window.output_3)
            self.window.start_button_3.setEnabled(True)
            return None

        self.output_signal.emit('Процесс начался, ожидайте', self.window.output_3)
        self.bar_signal.emit(0, self.window.up_bar)
        self.window.up_bar.show()
        self.stop.setEnabled(True)

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
            if self.stop_flag:
                raise Exception('Процесс остановлен')
            session.browser.get("https://www.olx.ua/myaccount/pro/?query=" + ids[i])
            if i == 0:
                time.sleep(3)
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
            toggle_button = session.wait('//div[@data-testid="flyout-toggle"]/button', timer=10)
            if toggle_button:
                toggle_button.click()
            else:
                tariff.append('')
                date.append('')
                timer.append('')
                for l in range(long):
                    dates[l].append('')
                    times[l].append('')
                self.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)
                self.output_signal.emit(ids[i] + ' - Объявление не рекламируется', self.window.output_3)
                continue
            if session.wait('//div[@data-testid="flyout-content"]'):
                divs = len(session.browser.find_elements(By.XPATH, '//div[@data-testid="flyout-content"]/div/div'))
                if divs > 1:
                    try:
                        index = 3
                        tariff_text = session.browser.find_element(
                            By.XPATH, '//div[@data-testid="flyout-content"]/div/div[1]/p[1]').text
                        tariff_time = session.browser.find_element(
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
                    self.output_signal.emit(ids[i] + ' - Ошибка', self.window.output_3)
                elif session.browser.find_element(
                        By.XPATH, f'//div[@data-testid="flyout-content"]/div/div[{index}]/p').text == 'Поднятие вверх списка':
                    table = session.browser.find_elements(
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
                self.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)
                self.output_signal.emit(ids[i] + ' - Объявление не рекламируется', self.window.output_3)
                continue
            self.bar_signal.emit((i + 1) / len(ids) * self.window.up_bar.maximum(), self.window.up_bar)

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
        write_excel(data, path, sheetname)
        self.output_signal.emit('Данные получены', self.window.output_3)
    except Exception as e:
        if not self.stop_flag:
            self.window.report(str(e), 'Поднятия')
            self.output_signal.emit(str(e), self.window.output_3)
    finally:
        self.stop.setEnabled(False)
        session.exit()
        self.window.up_bar.hide()
        self.window.start_button_3.setEnabled(True)
