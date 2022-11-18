# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from browser import Browser
from utils import preload, write_excel
from selenium.webdriver.common.by import By


def stat_excel(path, sheetname, id):
    excel_data_df = pd.read_excel(path, sheet_name=sheetname, converters={id: str})
    ids = excel_data_df[id].tolist()
    return ids


def stats(self):
    self.window.start_button_2.setEnabled(False)
    session = Browser(dir_path=self.window.driver_path)
    try:
        path = self.window.path_input_2.text()
        sheetname = self.window.sheet_input_2.text()
        id = self.window.id_input_2.text()
        if '' in (path, sheetname, id):
            self.output_signal.emit('Заполните все поля', self.window.output_2)
            self.window.start_button_2.setEnabled(True)
            return
        ids = stat_excel(path, sheetname, id)
        if not ids:
            return None

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
                inventory_button = session.wait('//div[@data-cy="inventory-stats"]/button', timer=10)
                if inventory_button:
                    inventory_button.click()
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
            elem = session.wait('//div[@data-cy="offer-stats-graph"]/div[2]')
            svg = elem.find_element(By.TAG_NAME, 'svg').get_attribute('innerHTML')
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
                if n not in data.keys():
                    data[n] = ['' for l in range(long)]
                data[n].append(nums[n])
            self.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
            long += 1

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
        self.output_signal.emit('Данные получены', self.window.output_2)
    except Exception as e:
        if not self.stop_flag:
            self.window.report(str(e), 'Статистика')
            self.output_signal.emit(str(e), self.window.output_2)
    finally:
        self.stop.setEnabled(False)
        session.exit()
        self.window.stat_bar.hide()
        self.window.start_button_2.setEnabled(True)
