# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from operations import Operation
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", filename="activation.log", level=logging.DEBUG)


class Activation(Operation):
    def activation_excel(self, path, sheet_name, id, date, timer):
        logging.debug("Reading Excel file")
        data = pd.read_excel(path, sheet_name=sheet_name)
        logging.info("Reading Excel file DONE")

        logging.debug("Data transformation")
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
        logging.info("Data transformation DONE")

        logging.debug("Data filtering")
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
        logging.info("Data filtering DONE")

        return {k: v for k, v in result.items() if v}
    
    def get_dates(self):
        logging.debug("Read input data")
        path = self.window.path_input_4.text()
        sheet_name = self.window.sheet_input_4.text()
        id = self.window.id_input_4.text()
        date = self.window.date_input_4.text()
        timer = self.window.time_input_4.text()
        logging.info("Read input data DONE")

        logging.debug("Data validation")
        if '' in (path, sheet_name, id, date, timer):
            self.thread.output_signal.emit('Заполните все поля', self.output)
            self.window.start_button_4.setEnabled(True)
            logging.warning("Data validation FAILED")
            return None
        logging.info("Data validation DONE")

        return self.activation_excel(path, sheet_name, id, date, timer)

    def activation(self):
        try:
            logging.debug("Get dates")
            dates = self.get_dates()
            if not dates:
                logging.warning("Get dates FAILED")
                return None
            logging.warning("Get dates DONE")

            logging.debug("Session preload")
            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.output)
                logging.warning("Session preload FAILED")
                return None
            logging.info("Session preload DONE")

            logging.debug("Start activation")
            self.thread.output_signal.emit('Активация запущена', self.output)
            while dates:
                for key in list(dates.keys()).copy():
                    if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                        for data in dates[key].copy():
                            logging.debug(f"{data[0]} - Advertisement activation")
                            status = self.activate(data)
                            if status == 100:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Объявление активировано', self.output)
                                self.window.report(data[0] + ' - Объявление активировано')
                                logging.info(f"{data[0]} - Advertisement activation DONE")
                            elif status == 200:
                                new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                                if new_key in dates:
                                    for lst in dates.pop(key):
                                        dates[new_key].append(lst)
                                else:
                                    dates[new_key] = dates.pop(key)
                                self.thread.output_signal.emit(data[0] + ' - Активация перенесена на 2 минуты', self.output)
                                logging.warning(f"{data[0]} - Activation delay")
                            elif status == 400:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Не найден', self.output)
                                self.window.audio('error')
                                self.window.report(data[0] + ' - Не найден')
                                logging.error(f"{data[0]} - Advertisement not found")
                            else:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(data[0] + ' - Объявление не активировано, ошибка', self.output)
                                self.window.audio('error')
                                self.window.report(data[0] + ' - Объявление не активировано, ошибка')
                                self.window.report(status, 'Activation')
                                logging.critical(f"{data[0]} - {status}")
                        logging.debug("Check empty dates")
                        logging.debug(f"{key}: {dates[key]}")
                        if not dates[key]:
                            dates.pop(key)
                            logging.info("Delete empty dates")
                            logging.info(", ".join(dates.keys()))
            self.thread.output_signal.emit('Активация выполненна', self.output)
            logging.info("Activation DONE")
        except Exception as e:
            self.window.report(str(e), 'Activation')
            self.thread.output_signal.emit('Активация остановлена, ошибка', self.output)
            self.window.report('Активация остановлена, ошибка')
            logging.critical(str(e))
        finally:
            self.session.exit()
            logging.debug("End activation")

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
