# -*- coding: utf-8 -*-

import json
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from browser import Browser, BrowserException


class BaseOperation:
    def __init__(self, thread, window, output):
        self.thread = thread
        self.window = window
        self.output = output

    def login_input(self, session):
        elem = session.wait('//form[@data-testid="login-form"]')
        if elem:
            email = elem.find_element(By.XPATH, '//input[@type="email"]')
            email.send_keys(self.window.login_text)
            password = elem.find_element(By.XPATH, '//input[@type="password"]')
            password.send_keys(self.window.pass_text)
            button = elem.find_element(By.XPATH, '//button[@data-testid="login-submit-button"]')
            ActionChains(session.browser).click(button).perform()
            return True

    def get_tokens(self, session):
        url = urlparse(session.browser.current_url)
        code = parse_qs(url.query)["code"][0]
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.window.client_id,
            "client_secret": self.window.client_secret,
            "scope": "v2 read write",
            "code": code,
        }
        response = requests.post("https://www.olx.ua/api/open/oauth/token", json=payload).json()
        tokens = {
            "access_token": response["access_token"],
            "refresh_token": response["refresh_token"],
        }
        with open("data/tokens.json", "w") as file:
            file.write(json.dumps(tokens, indent=4))

    def login(self):
        try:
            session = Browser(dir_path=self.window.driver_path, headless=True)
            session.browser.get(
                f"https://www.olx.ua/oauth/authorize/?client_id={self.window.client_id}&response_type=code&scope=read+write+v2"
            )
            if self.window.login_text and self.window.pass_text:
                self.login_input(session)
            if session.wait(
                path='//div[@data-testid="qa-user-dropdown"]',
                path2='//div[@class="userbox-dd__user-name"]',
                timer=0,
            ):
                self.get_tokens(session)
                self.thread.output_signal.emit("Вход выполнен", self.output)
            else:
                self.thread.output_signal.emit("Вход не выполнен", self.output)
        except BrowserException as e:
            self.window.report(str(e), "Браузер")
            self.thread.output_signal.emit(str(e), self.output)
        except Exception as e:
            self.window.report(str(e), "Логин")
        finally:
            session.exit()

    def refresh(self):
        with open("data/tokens.json", "r") as file:
            tokens = json.loads(file.read())
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.window.client_id,
            "client_secret": self.window.client_secret,
            "refresh_token": tokens["refresh_token"],
        }
        response = requests.post("https://www.olx.ua/api/open/oauth/token", json=payload)
        if response.status_code == 200:
            response_data = response.json()
            tokens = {
                "access_token": response_data["access_token"],
                "refresh_token": response_data["refresh_token"],
            }
            with open("data/tokens.json", "w") as file:
                file.write(json.dumps(tokens, indent=4))
        elif self.relogin():
            self.thread.output_signal.emit("Токен обновлен", self.output)
        else:
            self.window.report("Не удалось обновить токен", "Логин")
            self.thread.output_signal.emit("Не удалось обновить токен", self.output)

    def relogin(self):
        try:
            session = Browser(dir_path=self.window.driver_path, headless=True)
            if self.window.login_text and self.window.pass_text:
                session.browser.get(
                    f"https://www.olx.ua/oauth/authorize/?client_id={self.window.client_id}&response_type=code&scope=read+write+v2"
                )
                if self.login_input(session):
                    if session.wait(
                        path='//div[@data-testid="qa-user-dropdown"]',
                        path2='//div[@class="userbox-dd__user-name"]',
                        timer=0,
                    ):
                        self.get_tokens(session)
                        return True
        except Exception as e:
            self.window.report(str(e), "Relogin")
            return False

    # def preload(self):
    #     status = True
    #     try:
    #         self.session.load_cookies(self.window.cookies_location, "https://www.olx.ua")
    #         self.session.browser.refresh()
    #         if not self.session.wait(
    #             path='//div[@data-testid="qa-user-dropdown"]',
    #             path2='//div[@class="userbox-dd__user-name"]',
    #         ):
    #             self.thread.output_signal.emit("Перезайдите в аккаунт", self.output)
    #             status = False
    #         else:
    #             cookies_bar = self.session.wait('//div[@id="cookiesBar"]/button', timer=1, condition="click")
    #             if cookies_bar:
    #                 cookies_bar.click()
    #     except BrowserException as e:
    #         self.session.exit()
    #         self.window.report(str(e), "Browser")
    #         self.thread.output_signal.emit(str(e), self.output)
    #         status = False
    #     except Exception as e:
    #         self.session.exit()
    #         self.window.report(str(e), "Preload")
    #         self.thread.output_signal.emit(str(e), self.output)
    #         status = False
    #     finally:
    #         return status
    #
    # def hide_popup(self):
    #     time.sleep(3)
    #     accept_button = self.session.wait('//button[@data-cy="welcome-modal-accept"]', timer=5, condition="click")
    #     if accept_button:
    #         accept_button.click()
    #     close_button = self.session.wait('//button[@aria-label="Close"]', timer=5, condition="click")
    #     if close_button:
    #         close_button.click()
    #     dismiss_button = self.session.wait('//button[@data-cy="ads-reposting-dismiss"]', timer=5, condition="click")
    #     if dismiss_button:
    #         dismiss_button.click()

    @staticmethod
    def write_excel(data, path, sheet_name):
        df = pd.DataFrame(data)
        split_path = path.split(".")
        new_path = ".".join(split_path[:-1]) + "_new." + split_path[-1]
        df.to_excel(new_path, sheet_name=sheet_name, index=False)
