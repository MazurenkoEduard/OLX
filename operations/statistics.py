# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from browser import Browser
from utils import preload, write_excel


def stat_excel(path, sheetname, id):
    excel_data_df = pd.read_excel(path, sheet_name=sheetname, converters={id: str})
    ids = excel_data_df[id].tolist()
    return ids


def stats(self):
    try:
        self.window.start_button_2.setEnabled(False)
        session = Browser(dir_path=self.window.driver_path)

        path = self.window.path_input_2.text()
        sheetname = self.window.sheet_input_2.text()
        id = self.window.id_input_2.text()
        if '' in (path, sheetname, id):
            self.output_signal.emit('Заполните все поля', self.window.output_2)
            self.window.start_button_2.setEnabled(True)
            return
        ids = stat_excel(path, sheetname, id)

        if not preload(self, self.window.output_2, session):
            self.output_signal.emit('Процесс остановлен', self.window.output_2)
            self.window.start_button_2.setEnabled(True)
            return

        self.output_signal.emit('Процесс начался, ожидайте', self.window.output_2)
        self.bar_signal.emit(0, self.window.stat_bar)
        self.window.stat_bar.show()
        self.stop.setEnabled(True)

        data = {'Id': ids}
        long = 0

        for i in range(len(ids)):
            if self.stop_flag:
                raise Exception('Процесс остановлен')
            try:
                session.browser.get(f"https://www.olx.ua/myaccount/pro/?query={ids[i]}")
                if i == 0:
                    time.sleep(3)
                    if session.wait('//button[@data-cy="welcome-modal-accept"]', timer=10):
                        session.browser.find_element_by_xpath('//button[@data-cy="welcome-modal-accept"]').click()
                    if session.wait('//button[@aria-label="Close"]', timer=10):
                        time.sleep(1)
                        session.browser.find_element_by_xpath('//button[@aria-label="Close"]').click()
                    if session.wait('//button[@data-cy="ads-reposting-dismiss"]', timer=10):
                        time.sleep(1)
                        session.browser.find_element_by_xpath('//button[@data-cy="ads-reposting-dismiss"]').click()
                if session.wait('//div[@data-cy="inventory-stats"]/button', timer=10):
                    session.browser.find_element_by_xpath('//div[@data-cy="inventory-stats"]/button').click()
                else:
                    for k in list(data.keys())[1:]:
                        data[k].append('')
                    self.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
                    self.output_signal.emit(ids[i] + ' - Объявление не найдено', self.window.output_2)
                    long += 1
                    continue
            except Exception as e:
                self.window.report(str(e), 'Статистика')
                for k in list(data.keys())[1:]:
                    data[k].append('')
                self.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
                self.output_signal.emit(ids[i] + ' - Объявление не найдено', self.window.output_2)
                long += 1
                continue
            session.wait('//div[@data-cy="offer-stats-graph"]/div[2]')
            elem = session.browser.find_element_by_xpath('//div[@data-cy="offer-stats-graph"]/div[2]')
            svg = elem.find_element_by_tag_name('svg').get_attribute('innerHTML')
            soup = BeautifulSoup(svg, 'html.parser')
            gs = soup.find_all('g')
            all_g = gs[1].find_all('g')
            g = all_g[-1]
            date = g.find('tspan').getText()
            counts = gs[-2].find_all('text')
            numbers = {}
            for c in reversed(counts):
                try:
                    num = c.find('tspan').getText()
                    numbers[date] = num
                except Exception:
                    numbers[date] = ''
                date = (datetime.strptime(date, "%d.%m") - timedelta(days=1)).strftime("%d.%m")
            nums = dict(list(numbers.items()))
            for n in nums.keys():
                if not n in data.keys():
                    data[n] = ['' for l in range(long)]
                data[n].append(nums[n])
            self.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
            long += 1

        self.stop.setEnabled(False)
        session.exit()

        while True:
            dk = list(data.keys())
            if set(data[dk[-1]]) == {''}:
                data.pop(dk[-1])
            else:
                break
        items = list(data.items())
        id_column = items[:1]
        date_column = items[1:]
        date_column.reverse()
        data = dict(id_column + date_column)
        write_excel(data, path, sheetname)

        self.window.stat_bar.hide()
        self.output_signal.emit('Данные получены', self.window.output_2)
        self.window.start_button_2.setEnabled(True)
    except Exception as e:
        self.stop.setEnabled(False)
        session.exit()
        self.window.stat_bar.hide()
        if not self.stop_flag:
            self.window.report(str(e), 'Статистика')
            self.output_signal.emit(str(e), self.window.output_2)
        self.window.start_button_2.setEnabled(True)
