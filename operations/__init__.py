# -*- coding: utf-8 -*-

import time
import pandas as pd
from selenium.webdriver.common.action_chains import ActionChains
from browser import Browser, BrowserException
from selenium.webdriver.common.by import By


class Operation:
    def __init__(self, thread, window, output, headless=True):
        self.thread = thread
        self.window = window
        self.output = output
        self.session = Browser(dir_path=self.window.driver_path, headless=headless)

    def login(self):
        try:
            self.session.browser.get(
                "https://www.olx.ua/account/?ref%5B0%5D%5Baction%5D=myaccount&ref%5B0%5D%5Bmethod%5D=index#login")
            if self.window.login_text and self.window.pass_text:
                elem = self.session.wait('//section[@class="login-page has-animation"]')
                if elem:
                    email = elem.find_element(By.XPATH, '//input[@id="userEmail"]')
                    email.send_keys(self.window.login_text)
                    password = elem.find_element(By.XPATH, '//input[@id="userPass"]')
                    password.send_keys(self.window.pass_text)
                    button = elem.find_element(By.XPATH, '//button[@id="se_userLogin"]')
                    ActionChains(self.session.browser).click(button).perform()
            if self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                 path2='//div[@class="userbox-dd__user-name"]', timer=0):
                self.session.save_cookies(self.window.cookies_location, self.session.browser.get_cookies())
                self.thread.output_signal.emit('Вход выполнен', self.output)
            else:
                self.thread.output_signal.emit('Вход не выполнен', self.output)
        except BrowserException as e:
            self.window.report(str(e), 'Браузер')
            self.thread.output_signal.emit(str(e), self.output)
        except Exception as e:
            self.window.report(str(e), 'Логин')
        finally:
            self.session.exit()

    def relogin(self):
        try:
            if self.window.login_text and self.window.pass_text:
                self.session.browser.get(
                    "https://www.olx.ua/account/?ref%5B0%5D%5Baction%5D=myaccount&ref%5B0%5D%5Bmethod%5D=index#login")
                elem = self.session.wait('//section[@class="login-page has-animation"]')
                if elem:
                    email = elem.find_element(By.XPATH, '//input[@id="userEmail"]')
                    email.send_keys(self.window.login_text)
                    password = elem.find_element(By.XPATH, '//input[@id="userPass"]')
                    password.send_keys(self.window.pass_text)
                    button = elem.find_element(By.XPATH, '//button[@id="se_userLogin"]')
                    ActionChains(self.session.browser).click(button).perform()
                    if self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                         path2='//div[@class="userbox-dd__user-name"]'):
                        return True
                else:
                    return False
            else:
                return False
        except Exception as e:
            self.window.report(str(e), 'Relogin')
            return False

    def preload(self):
        status = True
        try:
            self.session.load_cookies(self.window.cookies_location, 'https://www.olx.ua')
            self.session.browser.refresh()
            if not self.session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                     path2='//div[@class="userbox-dd__user-name"]'):
                self.thread.output_signal.emit('Перезайдите в аккаунт', self.output)
                status = False
            else:
                cookies_bar = self.session.wait('//div[@id="cookiesBar"]/button', timer=1, condition="click")
                if cookies_bar:
                    cookies_bar.click()
        except BrowserException as e:
            self.window.report(str(e), 'Браузер')
            self.thread.output_signal.emit(str(e), self.output)
            status = False
        except Exception as e:
            self.window.report(str(e), 'Preload')
            self.thread.output_signal.emit(str(e), self.output)
            status = False
        finally:
            self.session.exit()
            return status

    def hide_popup(self):
        time.sleep(3)
        accept_button = self.session.wait('//button[@data-cy="welcome-modal-accept"]', timer=5, condition="click")
        if accept_button:
            accept_button.click()
        close_button = self.session.wait('//button[@aria-label="Close"]', timer=5, condition="click")
        if close_button:
            close_button.click()
        dismiss_button = self.session.wait('//button[@data-cy="ads-reposting-dismiss"]', timer=5, condition="click")
        if dismiss_button:
            dismiss_button.click()

    @staticmethod
    def write_excel(data, path, sheetname):
        df = pd.DataFrame(data)
        split_path = path.split('.')
        new_path = '.'.join(split_path[:-1]) + '_new.' + split_path[-1]
        df.to_excel(new_path, sheet_name=sheetname, index=False)
