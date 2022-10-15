# -*- coding: utf-8 -*-

import pandas as pd
from selenium.webdriver.common.action_chains import ActionChains
from browser import Browser, BrowserException


def login(self):
    try:
        session = Browser(dir_path=self.window.driver_path)
        session.driver(headless=False)
        session.browser.get("https://www.olx.ua/account/?ref%5B0%5D%5Baction%5D=myaccount&ref%5B0%5D%5Bmethod%5D=index#login")
        session.browser.maximize_window()
        if self.window.login_text and self.window.pass_text:
            session.wait('//section[@class="login-page has-animation"]')
            elem = session.browser.find_element_by_xpath('//section[@class="login-page has-animation"]')
            email = elem.find_element_by_xpath('//input[@id="userEmail"]')
            email.send_keys(self.window.login_text);
            password = elem.find_element_by_xpath('//input[@id="userPass"]')
            password.send_keys(self.window.pass_text)
            button = elem.find_element_by_xpath('//button[@id="se_userLogin"]')
            ActionChains(session.browser).click(button).perform()
        if session.wait(path='//div[@data-testid="qa-user-dropdown"]', path2='//div[@class="userbox-dd__user-name"]', timer=0):
            cookies = session.browser.get_cookies()
            session.exit()
            session.save_cookies(self.window.cookies_location, cookies)
            self.output_signal.emit('Вход выполнен', self.window.login_output)
        else:
            session.exit()
    except BrowserException as e:
        self.window.report(str(e), 'Браузер')
        self.output_signal.emit(str(e), self.window.login_output)
        session.exit()
    except Exception as e:
        self.window.report(str(e), 'Логин')
        session.exit()


def relogin(window, session):
    try:
        if window.login_text and window.pass_text:
            session.browser.get("https://www.olx.ua/account/?ref%5B0%5D%5Baction%5D=myaccount&ref%5B0%5D%5Bmethod%5D=index#login")
            if session.wait('//section[@class="login-page has-animation"]'):
                elem = session.browser.find_element_by_xpath('//section[@class="login-page has-animation"]')
                email = elem.find_element_by_xpath('//input[@id="userEmail"]')
                email.send_keys(window.login_text);
                password = elem.find_element_by_xpath('//input[@id="userPass"]')
                password.send_keys(window.pass_text)
                button = elem.find_element_by_xpath('//button[@id="se_userLogin"]')
                ActionChains(session.browser).click(button).perform()
                if session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                                path2='//div[@class="userbox-dd__user-name"]'):
                    return True
            else:
                return False
        else:
            return False
    except Exception as e:
        window.report(str(e), 'Relogin')
        return False


def preload(self, output, session, headless=True):
    try:
        session.driver(headless)
        session.load_cookies(self.window.cookies_location, 'https://www.olx.ua')
        session.browser.refresh()
        if not session.wait(path='//div[@data-testid="qa-user-dropdown"]',
                            path2='//div[@class="userbox-dd__user-name"]'):
            session.exit()
            self.output_signal.emit('Перезайдите в аккаунт', output)
            return False
        if session.wait('//div[@id="cookiesBar"]/button', timer=1):
            try:
                session.browser.find_element_by_xpath('//div[@id="cookiesBar"]/button').click()
            except Exception:
                pass
        return True
    except BrowserException as e:
        session.exit()
        self.window.report(str(e), 'Браузер')
        self.output_signal.emit(str(e), output)
        return False
    except Exception as e:
        session.exit()
        self.window.report(str(e), 'Preload')
        self.output_signal.emit(str(e), output)
        return False


def write_excel(data, path, sheetname):
    df = pd.DataFrame(data)
    split_path = path.split('.')
    new_path = '.'.join(split_path[:-1]) + '_new.' + split_path[-1]
    df.to_excel(new_path, sheet_name=sheetname, index=False)
