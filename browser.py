# -*- coding: utf-8 -*-

import os
import time
import pickle
import requests
import zipfile
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException
try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = os.open(os.devnull, os.O_RDWR)


class BrowserException(Exception):
    pass


class Browser:
    sessions = []

    def __init__(self, dir_path=None, proxy=None, headless=True):
        self.browser = None
        self.dir_path = dir_path
        self.proxy = proxy
        self.headless = headless
        self.__browser_wait = False
        self.__load_browser()

    def __load_driver(self, version):
        url = 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE_' + version
        re = requests.get(url)
        driver_version = re.text            
        driver = requests.get(
            "http://chromedriver.storage.googleapis.com/" + driver_version + "/chromedriver_win32.zip")
        with open(self.dir_path + 'chromedriver.zip', 'wb') as file:
            file.write(driver.content)
        zip_file = zipfile.ZipFile(self.dir_path + 'chromedriver.zip')
        zip_file.extractall(self.dir_path)
        zip_file.close()
        os.remove(self.dir_path + 'chromedriver.zip')

    def __config_browser(self):
        chrome_options = webdriver.ChromeOptions()
        if self.headless:
            chrome_options.add_argument('headless')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # hide selenium
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 OPR/94.0.0.0")
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # chrome_options.add_experimental_option("useAutomationExtension", False)
        if self.proxy:
            chrome_options.add_argument("--proxy-server=%s" % self.proxy)
        self.browser = webdriver.Chrome(executable_path=self.dir_path + 'chromedriver', chrome_options=chrome_options)
        self.__class__.sessions.append(self)

    def __load_browser(self):
        try:
            self.__browser_wait = True
            self.__config_browser()
        except Exception:
            try:
                sys_drive = os.getenv("SystemDrive")
                filepath = [r'wmic datafile where name="' + str(sys_drive) +
                            r'\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" get Version /value',
                            r'wmic datafile where name="' + str(sys_drive) +
                            r'\\Program Files\\Google\\Chrome\\Application\\chrome.exe" get Version /value']
                for path in filepath:
                    output = subprocess.check_output(path, shell=True, errors=None, stdin=DEVNULL, stderr=DEVNULL)
                    version = output.decode('utf-8').strip().replace('Version=', '')
                    if version.find('.') != -1:
                        version = '.'.join(version.split('.')[:-1])
                        self.__load_driver(version)
                        self.__config_browser()
                        break
                else:
                    raise Exception('Установите Google Chrome')
            except Exception as e:
                self.__browser_wait = False
                raise BrowserException(e)
        finally:
            self.__browser_wait = False

    def load_cookies(self, cookies_location, url=None):
        with open(cookies_location, 'rb') as cookies_file:
            cookies = pickle.load(cookies_file)
            self.browser.delete_all_cookies()
            self.browser.get("https://google.com" if url is None else url)
            for cookie in cookies:
                if isinstance(cookie.get('expiry'), float): 
                    cookie['expiry'] = int(cookie['expiry'])
                self.browser.add_cookie(cookie)

    def save_cookies(self, cookies_location, cookies=None):
        with open(cookies_location, 'wb') as file:
            if cookies:
                pickle.dump(cookies, file)
            else:
                pickle.dump(self.browser.get_cookies(), file)

    def wait(self, path, path2=None, timer=20, method=By.XPATH, condition="find"):
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
                    element = WebDriverWait(self.browser, timer).until(ec.any_of(
                        ec.element_to_be_clickable((method, path)),
                        ec.element_to_be_clickable((method, path2))))
                else:
                    element = WebDriverWait(self.browser, timer).until(ec.any_of(
                        ec.presence_of_element_located((method, path)),
                        ec.presence_of_element_located((method, path2))))
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
