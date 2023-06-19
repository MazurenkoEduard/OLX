# -*- coding: utf-8 -*-

import time
import pandas as pd
from operations import Operation
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", filename="activation.log", level=logging.DEBUG)


class Activation(Operation):
    def read_data(self):
        logging.debug("Read input data")
        self.naming = {
            'path': self.window.path_input_4.text(),
            'sheet_name': self.window.sheet_input_4.text(),
            'id': self.window.id_input_4.text(),
            'date': self.window.date_input_4.text(),
            'time': self.window.time_input_4.text(),
            'extension': 'Extension'
        }
        logging.info("Read input data DONE")

        logging.debug("Data validation")
        if '' in (self.naming['path'], self.naming['sheet_name'], self.naming['id'], self.naming['date'], self.naming['time']):
            self.thread.output_signal.emit('Заполните все поля', self.output)
            logging.warning("Data validation FAILED")
            return False
        else:
            logging.info("Data validation DONE")
            return True

    def activation_excel(self):
        logging.debug("Reading Excel file")
        df = pd.read_excel(self.naming['path'], sheet_name=self.naming['sheet_name'], keep_default_na=False,
                           converters={self.naming['id']: str})
        logging.info("Reading Excel file DONE")

        logging.debug("Data filtering")
        today = pd.Timestamp.today().date()
        now = pd.Timestamp.now().time()
        for row in df.iterrows():
            if not row[1][self.naming['id']]:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit('Не найден ID', self.output)
            elif not row[1][[self.naming['date'], self.naming['time']]].all():
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming['id']] + ' - Заполните все столбцы', self.output)
            elif row[1][self.naming['date']] < today or row[1][self.naming['time']] < now:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming['id']] + ' - Реклама не активированна, опоздание по времени', self.output)
        df.reset_index(drop=True, inplace=True)
        logging.info("Data filtering DONE")

        df[self.naming['extension']] = 0
        return df

    def activation_report(self, df, row, status, sound=False, report=None):
        df.drop(index=row[0], inplace=True)
        if sound:
            self.window.play_sound('error')
        if report:
            self.window.report(status, report)
            self.window.report(f"{row[1][self.naming['id']]} - Объявление не активировано, ошибка")
        else:
            self.window.report(f"{row[1][self.naming['id']]} - {status}")
        self.thread.output_signal.emit(f"{row[1][self.naming['id']]} - {status}", self.output)

    def activation(self):
        try:
            if not self.read_data():
                return None

            logging.debug("Get Excel data")
            data = self.activation_excel()
            if data.empty:
                logging.warning("Get Excel data FAILED")
                return None
            logging.warning("Get Excel data DONE")

            logging.debug("Session preload")
            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.output)
                logging.warning("Session preload FAILED")
                return None
            logging.info("Session preload DONE")

            logging.debug("Start activation")
            self.thread.output_signal.emit('Активация запущена', self.output)
            while not data.empty:
                today = pd.Timestamp.today().to_datetime64()
                now = pd.Timestamp.now().time()
                df = data[(data[self.naming['date']] <= today) & (data[self.naming['time']] <= now)]
                for row in df.iterrows():
                    logging.debug(f"{row[1][self.naming['id']]} - Advertisement activation")
                    status = self.activate(df, row)
                    if status == 100:
                        self.activation_report(df, row, 'Объявление активировано')
                        logging.info(f"{row[1][self.naming['id']]} - Advertisement activation DONE")
                    elif status == 200:
                        timestamp = pd.Timestamp(row[1][self.naming['date']].year, row[1][self.naming['date']].month,
                                                 row[1][self.naming['date']].day, row[1][self.naming['time']].hour,
                                                 row[1][self.naming['time']].minute) + pd.Timedelta(minutes=2)
                        df.loc[row[0], [self.naming['date'], self.naming['time']]] = [timestamp.date(), timestamp.time()]
                        self.thread.output_signal.emit(f"{row[1][self.naming['id']]} - Активация перенесена на 2 минуты", self.output)
                        logging.warning(f"{row[1][self.naming['id']]} - Activation delay")
                    elif status == 400:
                        self.activation_report(df, row, 'Не найден', sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Advertisement not found")
                    else:
                        self.activation_report(df, row, status, sound=True, report='Activation')
                        logging.critical(f"{row[1][self.naming['id']]} - {status}")
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

    def activate(self, df, row):
        try:
            link = 'https://www.olx.ua/d/myaccount/finished?query=' + row[1][self.naming['id']]
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
                if row[1][self.naming['extension']] < 5:
                    df.loc[row[0], self.naming['extension']] += 1
                    return 200
                else:
                    return 400
        except Exception as e:
            return str(e)
