# -*- coding: utf-8 -*-

import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from browser import Browser
from selenium.webdriver.common.by import By
from operations import Operation


class Statistic(Operation):
    def statistic_excel(self, path, sheetname, id):
        excel_data_df = pd.read_excel(path, sheet_name=sheetname, converters={id: str})
        ids = excel_data_df[id].tolist()
        return ids
    
    def statistics(self):
        self.window.start_button_2.setEnabled(False)
        self.session = Browser(dir_path=self.window.driver_path)
        try:
            path = self.window.path_input_2.text()
            sheetname = self.window.sheet_input_2.text()
            id = self.window.id_input_2.text()
            if '' in (path, sheetname, id):
                self.thread.output_signal.emit('Заполните все поля', self.window.output_2)
                self.window.start_button_2.setEnabled(True)
                return
            ids = self.statistic_excel(path, sheetname, id)
            if not ids:
                return None
    
            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.window.output_2)
                self.window.start_button_2.setEnabled(True)
                return
    
            self.thread.output_signal.emit('Процесс начался, ожидайте', self.window.output_2)
            self.thread.bar_signal.emit(0, self.window.stat_bar)
            self.window.stat_bar.show()
    
            data = {'Id': ids}
            long = 0
    
            for i in range(len(ids)):
                try:
                    self.session.browser.get(f"https://www.olx.ua/myaccount/pro/?query={ids[i]}")
                    if i == 0:
                        self.hide_popup()
                    inventory_button = self.session.wait('//div[@data-cy="inventory-stats"]/button', timer=10, condition="click")
                    if inventory_button:
                        inventory_button.click()
                    else:
                        for k in list(data.keys())[1:]:
                            data[k].append('')
                        self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
                        self.thread.output_signal.emit(ids[i] + ' - Объявление не найдено', self.window.output_2)
                        long += 1
                        continue
                except Exception as e:
                    self.window.report(str(e), 'Статистика')
                    for k in list(data.keys())[1:]:
                        data[k].append('')
                    self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
                    self.thread.output_signal.emit(ids[i] + ' - Объявление не найдено', self.window.output_2)
                    long += 1
                    continue
                elem = self.session.wait('//div[@data-cy="offer-stats-graph"]/div[2]')
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
                self.thread.bar_signal.emit((i + 1) / len(ids) * self.window.stat_bar.maximum(), self.window.stat_bar)
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
            self.write_excel(data, path, sheetname)
            self.thread.output_signal.emit('Данные получены', self.window.output_2)
        except Exception as e:
            self.window.report(str(e), 'Статистика')
            self.thread.output_signal.emit(str(e), self.window.output_2)
        finally:
            self.session.exit()
            self.window.stat_bar.hide()
