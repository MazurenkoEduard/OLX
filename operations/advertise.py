# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from operations import Operation


class Advertise(Operation):
    def ad_excel(self, path, sheetname, id, date, timer, tariff, service):
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
        tariffs = data[tariff].tolist()
        for i in range(len(tariffs)):
            if pd.isnull(tariffs[i]):
                tariffs[i] = ''
        services = data[service].tolist()
        for i in range(len(services)):
            if pd.isnull(services[i]):
                services[i] = ''
        result = {dates[i] + ' ' + times[i]: [] for i in range(len(ids))}
        today = time.strftime("%Y.%m.%d", time.localtime())
        for i in range(len(ids)):
            if not (ids[i] and dates[i] and times[i]):
                self.thread.output_signal.emit(ids[i] + ' - Заполните все столбцы', self.output)
            elif not (tariffs[i] or services[i]):
                self.thread.output_signal.emit(ids[i] + ' - Не выбран тариф', self.output)
            elif dates[i] < today:
                self.thread.output_signal.emit(ids[i] + ' - Реклама не оплачена, опоздание по времени', self.output)
            elif dates[i] > today:
                result[dates[i] + ' ' + times[i]].append([ids[i], tariffs[i], services[i], 0])
            elif dates[i] == today:
                if datetime.strptime(datetime.now().strftime('%H:%M'), '%H:%M') <= datetime.strptime(times[i], '%H:%M'):
                    result[dates[i] + ' ' + times[i]].append([ids[i], tariffs[i], services[i], 0])
                else:
                    self.thread.output_signal.emit(ids[i] + ' - Реклама не оплачена, опоздание по времени', self.output)

        return {k: v for k, v in result.items() if v}

    def get_dates(self):
        path = self.window.path_input_1.text()
        sheetname = self.window.sheet_input_1.text()
        id = self.window.id_input_1.text()
        date = self.window.date_input_1.text()
        timer = self.window.time_input_1.text()
        tariff = self.window.tariff_input_1.text()
        service = self.window.service_input_1.text()
        if '' in (path, sheetname, id, date, timer, tariff, service):
            self.thread.output_signal.emit('Заполните все поля', self.output)
            self.window.start_button_1.setEnabled(True)
            return None
        return self.ad_excel(path, sheetname, id, date, timer, tariff, service)

    def advertise(self):
        try:
            dates = self.get_dates()
            if not dates:
                return None

            if not self.preload():
                self.thread.output_signal.emit('Процесс остановлен', self.output)
                return None

            self.thread.output_signal.emit('Реклама запущена', self.output)

            while dates:
                for key in list(dates.keys()).copy():
                    if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                        for data in dates[key].copy():
                            status = self.pay(data)
                            if status == 100:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама оплачена', self.output)
                                self.window.report(f'{data[0]} - Реклама оплачена')
                            elif status == 101:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Срок действия услуги превышает срок размещения объявления', self.output)
                                self.window.audio('error')
                                self.window.report(f'{data[0]} - Срок действия услуги превышает срок размещения объявления')
                            elif status == 200:
                                new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                                if new_key in dates:
                                    for lst in dates.pop(key):
                                        dates[new_key].append(lst)
                                else:
                                    dates[new_key] = dates.pop(key)
                                self.thread.output_signal.emit(f'{data[0]} - Оплата рекламы перенесена на 2 минуты', self.output)
                            elif status == 400:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама не оплачена, опоздание по времени', self.output)
                                self.window.audio('error')
                                self.window.report(f'{data[0]} - Реклама не оплачена, опоздание по времени')
                            elif status == 401:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама не оплачена, недостаточно средств', self.output)
                                self.window.audio('error')
                                self.window.report(f'{data[0]} - Реклама не оплачена, недостаточно средств')
                            elif status == 402:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама не оплачена, проблемы с соединением', self.output)
                                self.window.audio('error')
                                self.window.report(f'{data[0]} - Реклама не оплачена, проблемы с соединением')
                            elif status == 403:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама не оплачена, не найден тариф', self.output)
                                self.window.audio('error')
                                self.window.report(f'{data[0]} - Реклама не оплачена, не найден тариф')
                            else:
                                dates[key].remove(data)
                                self.thread.output_signal.emit(f'{data[0]} - Реклама не оплачена, ошибка', self.output)
                                self.window.audio('error')
                                self.window.report(status, 'Оплата')
                                self.window.report(f'{data[0]} - Реклама не оплачена, ошибка')
                        if not dates[key]:
                            dates.pop(key)
            self.thread.output_signal.emit('Все объявления прорекламированы', self.output)
        except Exception as e:
            self.window.report(str(e), 'Реклама')
            self.thread.output_signal.emit('Реклама остановлена, ошибка', self.output)
            self.window.report('Реклама остановлена, ошибка')
        finally:
            self.session.exit()

    def pay(self, data):
        try:
            link = "https://www.olx.ua/bundles/promote/?id=" + data[0] + "&bs=myaccount_promoting"
            self.session.browser.get(link)
            if not self.session.wait('//div[@class="css-k1bey5"]'):
                if not self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                         path2='//div[@class="userbox-dd__user-name"]'):
                    if self.relogin():
                        self.session.browser.get(link)
                        if not self.session.wait('//div[@class="css-k1bey5"]'):
                            return 'Relogin Error'
                    else:
                        return 'Relogin Error'
                else:
                    return 'Error'
            tariffs = self.session.browser.find_elements(By.XPATH, '//div[@class="css-k1bey5"]/div')
            if data[1]:
                if data[1].find('Легкий старт') != -1:
                    class_name = tariffs[0]
                elif data[1].find('Быстрая продажа') != -1:
                    class_name = tariffs[1]
                elif data[1].find('Турбо продажа') != -1:
                    class_name = tariffs[2]
                else:
                    return 403

                if class_name.get_attribute('disabled'):
                    if data[3] < 5:
                        data[3] += 1
                        return 200
                    else:
                        return 400
                elif class_name.get_attribute('class').find("css-fujbfz") == -1:
                    class_name.click()
            else:
                class_name = tariffs[1]
                if class_name.get_attribute('class').find("css-1fgr50i") != -1:
                    class_name.click()

            if data[2]:
                services = self.session.browser.find_elements(By.XPATH, '//div[@data-cy="vas-item"]')
                if data[2].find('7 поднятий в верх списка') != -1:
                    services[0].click()
                elif data[2].find('VIP-объявление на 7 дней') != -1:
                    services[1].click()
                elif data[2].find('Топ-объявление на 7 дней') != -1:
                    services[2].click()
                    self.session.browser.find_element(By.XPATH, '//div[@data-testid="dropdown-head"]').click()
                elif data[2].find('Топ-объявление на 30 дней') != -1:
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
