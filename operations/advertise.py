# -*- coding: utf-8 -*-

import time
import pandas as pd
from datetime import datetime, timedelta
from browser import Browser
from utils import preload, relogin


def ad_excel(self, path, sheetname, id, date, timer, tariff1, tariff2):
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
    tariffs1 = data[tariff1].tolist()
    for i in range(len(tariffs1)):
        if pd.isnull(tariffs1[i]):
            tariffs1[i] = ''
    tariffs2 = data[tariff2].tolist()
    for i in range(len(tariffs2)):
        if pd.isnull(tariffs2[i]):
            tariffs2[i] = ''
    result = {dates[i] + ' ' + times[i]: [] for i in range(len(ids))}
    today = time.strftime("%Y.%m.%d", time.localtime())
    for i in range(len(ids)):
        if not (ids[i] and dates[i] and times[i]):
            self.output_signal.emit(ids[i] + ' - Заполните все столбцы', self.window.output_1)
        elif not (tariffs1[i] or tariffs2[i]):
            self.output_signal.emit(ids[i] + ' - Не выбран тариф', self.window.output_1)
        elif dates[i] < today:
            self.output_signal.emit(ids[i] + ' - Реклама не оплачена, опоздание по времени', self.window.output_1)
        elif dates[i] > today:
            result[dates[i] + ' ' + times[i]].append([ids[i], tariffs1[i], tariffs2[i], 0])
        elif dates[i] == today:
            if datetime.strptime(datetime.now().strftime('%H:%M'), '%H:%M') <= datetime.strptime(times[i], '%H:%M'):
                result[dates[i] + ' ' + times[i]].append([ids[i], tariffs1[i], tariffs2[i], 0])
            else:
                self.output_signal.emit(ids[i] + ' - Реклама не оплачена, опоздание по времени', self.window.output_1)

    return {k: v for k, v in result.items() if v}


def advertise(self):
    try:
        self.window.start_button_1.setEnabled(False)
        session = Browser(dir_path=self.window.driver_path)

        path = self.window.path_input_1.text()
        sheetname = self.window.sheet_input_1.text()
        id = self.window.id_input_1.text()
        date = self.window.date_input_1.text()
        timer = self.window.time_input_1.text()
        tariff1 = self.window.tariff_input_1.text()
        tariff2 = self.window.addit_input_1.text()
        if '' in (path, sheetname, id, date, timer, tariff1, tariff2):
            self.output_signal.emit('Заполните все поля', self.window.output_1)
            self.window.start_button_1.setEnabled(True)
            return
        dates = ad_excel(self, path, sheetname, id, date, timer, tariff1, tariff2)

        if not preload(self, self.window.output_1, session):
            self.output_signal.emit('Процесс остановлен', self.window.output_1)
            self.window.start_button_1.setEnabled(True)
            return

        self.output_signal.emit('Реклама запущена', self.window.output_1)
        self.stop.setEnabled(True)
        del_data = []
        del_keys = []
        replace_keys = []
        while dates:
            for key in dates.keys():
                if self.stop_flag:
                    raise Exception('Реклама остановлена')
                if time.strptime(key, "%Y.%m.%d %H:%M") <= time.localtime():
                    for data in dates[key]:
                        status = pay(self.window, session, data)
                        if status == 0:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Реклама не оплачена, опоздание по времени', self.window.output_1)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Реклама не оплачена, опоздание по времени')
                        elif status == 1:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Реклама оплачена', self.window.output_1)
                            self.window.report(data[0] + ' - Реклама оплачена')
                        elif status == 2:
                            replace_keys.append(key)
                            self.output_signal.emit(data[0] + ' - Оплата рекламы перенесена на 2 минуты', self.window.output_1)
                        elif status == 3:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Реклама не оплачена, недостаточно средств', self.window.output_1)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Реклама не оплачена, недостаточно средств')
                        elif status == 4:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Срок действия услуги превышает срок размещения объявления', self.window.output_1)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Срок действия услуги превышает срок размещения объявления')
                        elif status == 5:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Реклама не оплачена, проблемы с соединением', self.window.output_1)
                            self.window.audio('error')
                            self.window.report(data[0] + ' - Реклама не оплачена, проблемы с соединением')
                        else:
                            del_data.append(data)
                            self.output_signal.emit(data[0] + ' - Реклама не оплачена, ошибка', self.window.output_1)
                            self.window.audio('error')
                            self.window.report(status, 'Оплата')
                            self.window.report(data[0] + ' - Реклама не оплачена, ошибка')
                    for data in del_data:
                        dates[key].remove(data)
                    if not dates[key]:
                        del_keys.append(key)
            for key in replace_keys:
                new_key = (datetime.strptime(key, "%Y.%m.%d %H:%M") + timedelta(minutes=2)).strftime("%Y.%m.%d %H:%M")
                if new_key in dates:
                    for lst in dates.pop(key):
                        dates[new_key].append(lst)
                else:
                    dates[new_key] = dates.pop(key)
            for key in del_keys:
                dates.pop(key)
            del_data.clear()
            del_keys.clear()
            replace_keys.clear()
        self.stop.setEnabled(False)
        session.exit()
        self.output_signal.emit('Все объявления прорекламированы', self.window.output_1)
        self.window.start_button_1.setEnabled(True)
    except Exception as e:
        self.stop.setEnabled(False)
        session.exit()
        if not self.stop_flag:
            self.window.report(str(e), 'Реклама')
            self.output_signal.emit('Реклама остановлена, ошибка', self.window.output_1)
            self.window.report('Реклама остановлена, ошибка')
        self.window.start_button_1.setEnabled(True)


def pay(window, session, data):
    try:
        link = "https://www.olx.ua/bundles/promote/?id=" + data[0] + "&bs=myaccount_promoting"
        session.browser.get(link)
        if not session.wait('//div[@class="css-k1bey5"]'):
            if not session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                path2='//div[@class="userbox-dd__user-name"]'):
                if relogin(window, session):
                    session.browser.get(link)
                    if not session.wait('//div[@class="css-k1bey5"]'):
                        return 'Relogin Error'
                else:
                    return 'Relogin Error'
            else:
                return 'Error'
        PayElems1 = session.browser.find_elements_by_xpath('//div[@class="css-k1bey5"]/div')
        if data[1]:
            if data[1].find('Легкий старт') != -1:
                class_name = PayElems1[0]
            elif data[1].find('Быстрая продажа') != -1:
                class_name = PayElems1[1]
            elif data[1].find('Турбо продажа') != -1:
                class_name = PayElems1[2]

            if class_name.get_attribute('disabled'):
                if data[3] < 5:
                    data[3] += 1
                    return 2
                else:
                    return 0
            elif class_name.get_attribute('class').find("css-fujbfz") == -1:
                class_name.click()
        else:
            class_name = PayElems1[1]
            if class_name.get_attribute('class').find("css-1fgr50i") != -1:
                class_name.click()
        if data[2]:
            PayElems2 = session.browser.find_elements_by_xpath('//div[@data-cy="vas-item"]')
            if data[2].find('7 поднятий в верх списка') != -1:
                PayElems2[0].click()
            if data[2].find('VIP-объявление на 7 дней') != -1:
                PayElems2[1].click()
            if data[2].find('Топ-объявление на 7 дней') != -1:
                PayElems2[2].click()
                session.browser.find_element_by_xpath('//div[@data-testid="dropdown-head"]').click()
                # time.sleep(1)
                # session.browser.find_elements_by_xpath('//li[@data-testid="dropdown-item"]')[0].click()
            elif data[2].find('Топ-объявление на 30 дней') != -1:
                PayElems2[2].click()
                session.browser.find_element_by_xpath('//div[@data-testid="dropdown-head"]').click()
                time.sleep(1)
                session.browser.find_elements_by_xpath('//li[@data-testid="dropdown-item"]')[1].click()
        try:
            session.browser.find_element_by_xpath('//section[@class="css-js4vyd"]')
        except Exception:
            active = 1
        else:
            active = 4

        if session.wait('//button[@data-cy="dismiss-cookies-overlay"]'):
            session.browser.find_element_by_xpath('//button[@data-cy="dismiss-cookies-overlay"]').click()
        session.browser.find_element_by_xpath('//button[@data-cy="purchase-pay-button"]').click()
        session.wait('//div[@data-testid="provider-account"]')
        try:
            class_name = session.browser.find_element_by_xpath('//div[@data-testid="provider-account"]')
            if class_name.get_attribute("class").find('disabled') != -1:
                return 3
            elif class_name.get_attribute("class").find('selected') == -1:
                class_name.click()
        except Exception as e:
            return str(e)

        session.browser.find_element_by_xpath('//button[@data-cy="purchase-pay-button"]').click()  # ОПЛАТА!!!
        if not session.wait('//div[@data-cy="purchase-confirmation-page[success]"]', timer=10):
            return 5
        return active
    except Exception as e:
        return str(e)