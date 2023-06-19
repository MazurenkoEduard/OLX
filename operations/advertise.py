# -*- coding: utf-8 -*-

import time
import pandas as pd
from selenium.webdriver.common.by import By
from operations import Operation
import logging

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", filename="advertise.log", level=logging.DEBUG)


class Advertise(Operation):
    def read_data(self):
        logging.debug("Read input data")
        self.naming = {
            'path': self.window.path_input_1.text(),
            'sheet_name': self.window.sheet_input_1.text(),
            'id': self.window.id_input_1.text(),
            'date': self.window.date_input_1.text(),
            'time': self.window.time_input_1.text(),
            'tariff': self.window.tariff_input_1.text(),
            'service': self.window.service_input_1.text(),
            'extension': 'Extension'
        }
        logging.info("Read input data DONE")

        logging.debug("Data validation")
        if '' in (self.naming['path'], self.naming['sheet_name'], self.naming['id'], self.naming['date'],
                  self.naming['time'], self.naming['tariff'], self.naming['service']):
            self.thread.output_signal.emit('Заполните все поля', self.output)
            logging.warning("Data validation FAILED")
            return False
        else:
            logging.info("Data validation DONE")
            return True

    def advertise_excel(self):
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
            elif not row[1][[self.naming['tariff'], self.naming['service']]].any():
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming['id']] + ' - Не выбран тариф', self.output)
            elif row[1][self.naming['date']] < today or row[1][self.naming['time']] < now:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming['id']] + ' - Реклама не оплачена, опоздание по времени', self.output)
        df.reset_index(drop=True, inplace=True)
        logging.info("Data filtering DONE")

        df[self.naming['extension']] = 0
        return df

    def advertise_report(self, df, row, status, sound=False, report=None):
        df.drop(index=row[0], inplace=True)
        if sound:
            self.window.play_sound('error')
        if report:
            self.window.report(status, report)
            self.window.report(f"{row[1][self.naming['id']]} - Реклама не оплачена, ошибка")
        else:
            self.window.report(f"{row[1][self.naming['id']]} - {status}")
        self.thread.output_signal.emit(f"{row[1][self.naming['id']]} - {status}", self.output)

    def advertise(self):
        try:
            if not self.read_data():
                return None

            logging.debug("Get Excel data")
            data = self.advertise_excel()
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

            logging.debug("Start advertising")
            self.thread.output_signal.emit('Реклама запущена', self.output)
            while not data.empty:
                today = pd.Timestamp.today().to_datetime64()
                now = pd.Timestamp.now().time()
                df = data[(data[self.naming['date']] <= today) & (data[self.naming['time']] <= now)]
                for row in df.iterrows():
                    logging.debug(f"{row[1][self.naming['id']]} - Advertising payment")
                    status = self.payment(df, row)
                    if status == 100:
                        self.advertise_report(df, row, 'Реклама оплачена')
                        logging.info(f"{row[1][self.naming['id']]} - Advertising payment DONE")
                    elif status == 101:
                        self.advertise_report(df, row, 'Срок действия услуги превышает срок размещения объявления', sound=True)
                        logging.warning(f"{row[1][self.naming['id']]} - Posting period exceeded")
                    elif status == 200:
                        timestamp = pd.Timestamp(row[1][self.naming['date']].year, row[1][self.naming['date']].month,
                                                 row[1][self.naming['date']].day, row[1][self.naming['time']].hour,
                                                 row[1][self.naming['time']].minute) + pd.Timedelta(minutes=2)
                        df.loc[row[0], [self.naming['date'], self.naming['time']]] = [timestamp.date(), timestamp.time()]
                        self.thread.output_signal.emit(f"{row[1][self.naming['id']]} - Оплата рекламы перенесена на 2 минуты", self.output)
                        logging.warning(f"{row[1][self.naming['id']]} - Payment delay")
                    elif status == 400:
                        self.advertise_report(df, row, 'Реклама не оплачена, опоздание по времени', sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Late payment")
                    elif status == 401:
                        self.advertise_report(df, row, 'Реклама не оплачена, недостаточно средств', sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Insufficient funds")
                    elif status == 402:
                        self.advertise_report(df, row, 'Реклама не оплачена, проблемы с соединением', sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Problems with connection")
                    elif status == 403:
                        self.advertise_report(df, row, 'Реклама не оплачена, не найден тариф', sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Tariff not found")
                    else:
                        self.advertise_report(df, row, status, sound=True, report='Payment')
                        logging.critical(f"{row[1][self.naming['id']]} - {status}")
            self.thread.output_signal.emit('Все объявления прорекламированы', self.output)
            logging.info("Advertising DONE")
        except Exception as e:
            self.window.report(str(e), 'Advertise')
            self.thread.output_signal.emit('Реклама остановлена, ошибка', self.output)
            self.window.report('Реклама остановлена, ошибка')
            logging.critical(str(e))
        finally:
            self.session.exit()
            logging.debug("End advertising")

    def payment(self, df, row):
        try:
            link = "https://www.olx.ua/bundles/promote/?id=" + row[1][self.naming['id']] + "&bs=myaccount_promoting"
            self.session.browser.get(link)
            if not self.session.wait('//div[@class="css-k1bey5"]'):
                if not self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                         path2='//div[@class="userbox-dd__user-name"]'):
                    if self.relogin():
                        self.session.browser.get(link)
                        if not self.session.wait('//div[@class="css-k1bey5"]'):
                            return 'Not found error'
                    else:
                        return 'Relogin error'
                else:
                    return 'Login error'
            tariffs = self.session.browser.find_elements(By.XPATH, '//div[@class="css-k1bey5"]/div')
            if row[1][self.naming['tariff']]:
                if row[1][self.naming['tariff']].find('Легкий старт') != -1:
                    class_name = tariffs[0]
                elif row[1][self.naming['tariff']].find('Быстрая продажа') != -1:
                    class_name = tariffs[1]
                elif row[1][self.naming['tariff']].find('Турбо продажа') != -1:
                    class_name = tariffs[2]
                else:
                    return 403

                if class_name.get_attribute('disabled'):
                    if row[1][self.naming['extension']] < 5:
                        df.loc[row[0], self.naming['extension']] += 1
                        return 200
                    else:
                        return 400
                elif class_name.get_attribute('class').find("css-fujbfz") == -1:
                    class_name.click()
            else:
                class_name = tariffs[1]
                if class_name.get_attribute('class').find("css-1fgr50i") != -1:
                    class_name.click()

            if row[1][self.naming['service']]:
                services = self.session.browser.find_elements(By.XPATH, '//div[@data-cy="vas-item"]')
                if row[1][self.naming['service']].find('7 поднятий в верх списка') != -1:
                    services[0].click()
                elif row[1][self.naming['service']].find('VIP-объявление на 7 дней') != -1:
                    services[1].click()
                elif row[1][self.naming['service']].find('Топ-объявление на 7 дней') != -1:
                    services[2].click()
                    self.session.browser.find_element(By.XPATH, '//div[@data-testid="dropdown-head"]').click()
                elif row[1][self.naming['service']].find('Топ-объявление на 30 дней') != -1:
                    services[2].click()
                    self.session.browser.find_element(By.XPATH, '//div[@data-testid="dropdown-head"]').click()
                    time.sleep(1)
                    self.session.browser.find_elements(By.XPATH, '//li[@data-testid="dropdown-item"]')[1].click()
                else:
                    return 403

            if self.session.wait('//section[@class="css-js4vyd"]'):
                status = 101
            else:
                status = 100

            cookies_overlay = self.session.wait('//button[@data-cy="dismiss-cookies-overlay"]', condition="click")
            if cookies_overlay:
                self.session.browser.find_element(By.XPATH, '//button[@data-cy="dismiss-cookies-overlay"]').click()
            self.session.browser.find_element(By.XPATH, '//button[@data-cy="purchase-pay-button"]').click()

            pay_method = self.session.wait(By.XPATH, '//div[@data-testid="provider-account"]')
            if pay_method.get_attribute("class").find('disabled') != -1:
                return 401
            elif pay_method.get_attribute("class").find('selected') == -1:
                pay_method.click()
            self.session.browser.find_element(By.XPATH, '//button[@data-cy="purchase-pay-button"]').click()

            if not self.session.wait('//div[@data-cy="purchase-confirmation-page[success]"]', timer=10):
                return 402
            else:
                return status
        except Exception as e:
            return str(e)
