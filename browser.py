# -*- coding: utf-8 -*-

import os
import pickle
import time
from typing import Any, Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = os.open(os.devnull, os.O_RDWR)


class BrowserException(Exception):
    pass


class Browser:
    sessions = []

    def __init__(self, dir_path: str = "", proxy: str = "", headless: bool = True):
        self.browser: Optional[Chrome] = None
        self.dir_path: str = dir_path
        self.proxy: str = proxy
        self.headless: bool = headless
        self.__browser_wait: bool = False
        self.__load_browser()

    def __config_browser(self):
        chrome_options = ChromeOptions()
        if self.headless:
            chrome_options.add_argument("headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # hide selenium
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 OPR/94.0.0.0")
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # chrome_options.add_experimental_option("useAutomationExtension", False)
        if self.proxy:
            chrome_options.add_argument("--proxy-server=%s" % self.proxy)
        self.browser = Chrome(ChromeDriverManager(version="latest").install(), chrome_options=chrome_options)
        self.__class__.sessions.append(self)

    def __load_browser(self):
        try:
            self.__browser_wait = True
            self.__config_browser()
        except Exception as e:
            self.__browser_wait = False
            raise BrowserException(e)
        finally:
            self.__browser_wait = False

    def load_cookies(self, cookies_location: str, url: str = ""):
        with open(cookies_location, "rb") as cookies_file:
            cookies = pickle.load(cookies_file)
            self.browser.delete_all_cookies()
            self.browser.get("https://google.com" if url is None else url)
            for cookie in cookies:
                if isinstance(cookie.get("expiry"), float):
                    cookie["expiry"] = int(cookie["expiry"])
                self.browser.add_cookie(cookie)

    def save_cookies(self, cookies_location: str, cookies: Optional[Any] = None):
        with open(cookies_location, "wb") as file:
            if cookies:
                pickle.dump(cookies, file)
            else:
                pickle.dump(self.browser.get_cookies(), file)

    def wait(self, path: str, path2: str = "", timer: int = 20, method: str = By.XPATH, condition: str = "find"):
        try:
            if timer == 0:
                timer = 300
            if not path2:
                if condition == "click":
                    element = WebDriverWait(self.browser, timer).until(ec.element_to_be_clickable((method, path)))
                else:
                    element = WebDriverWait(self.browser, timer).until(ec.presence_of_element_located((method, path)))
            else:
                if condition == "click":
                    element = WebDriverWait(self.browser, timer).until(
                        ec.any_of(
                            ec.element_to_be_clickable((method, path)),
                            ec.element_to_be_clickable((method, path2)),
                        )
                    )
                else:
                    element = WebDriverWait(self.browser, timer).until(
                        ec.any_of(
                            ec.presence_of_element_located((method, path)),
                            ec.presence_of_element_located((method, path2)),
                        )
                    )
            return element
        except TimeoutException:
            return None

    def exit(self):
        if self.browser:
            while self.__browser_wait:
                time.sleep(1)
            self.browser.quit()
            self.__class__.sessions.remove(self)
            self.browser = None

    @classmethod
    def clear_sessions(cls):
        while cls.sessions:
            cls.sessions[0].exit()
