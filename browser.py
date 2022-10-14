# -*- coding: utf-8 -*-

import os
import time
import pickle
import requests
import zipfile
import subprocess
from selenium import webdriver as web
from seleniumwire import webdriver as wire_web
from selenium.webdriver.common.by import By

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = os.open(os.devnull, os.O_RDWR)


class BrowserException(Exception):
    pass


sessions = []


class Browser:
    def __init__(self, dir_path='', proxy=None):
        self.dir_path = dir_path
        self.browser = None
        self._browser_wait = False
        self.proxy = proxy
        sessions.append(self)

    def _load_driver(self, version):
        url = 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE_' + version
        re = requests.get(url)
        driver_version = re.text            
        driver = requests.get("http://chromedriver.storage.googleapis.com/" + driver_version + "/chromedriver_win32.zip")
        with open(self.dir_path + 'chromedriver.zip', 'wb') as file:
            file.write(driver.content)
        zip = zipfile.ZipFile(self.dir_path + 'chromedriver.zip')            
        zip.extractall(self.dir_path) 
        zip.close()
        os.remove(self.dir_path + 'chromedriver.zip')

    def _load_browser(self, headless):
        chrome_options = web.ChromeOptions()
        if headless:
            chrome_options.add_argument('headless')
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")             
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])            
        if self.proxy:
            wire_options = {
                'proxy': {
                    'http': 'http://' + self.proxy,
                    'https': 'https://' + self.proxy,
                    'no_proxy': 'localhost,127.0.0.1'
                    }
                }
            self.browser = wire_web.Chrome(executable_path=self.dir_path + 'chromedriver', seleniumwire_options=wire_options, options=chrome_options)
        else:
            self.browser = web.Chrome(executable_path=self.dir_path + 'chromedriver', chrome_options=chrome_options)
        self.browser.set_window_size(1920, 1080)

    def driver(self, headless=True):
        try:
            self._browser_wait = True
            self._load_browser(headless)
        except Exception:
            try:
                sys_drive = os.getenv("SystemDrive")
                filepath = [r'wmic datafile where name="' + str(sys_drive) + r'\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" get Version /value',
                            r'wmic datafile where name="' + str(sys_drive) + r'\\Program Files\\Google\\Chrome\\Application\\chrome.exe" get Version /value']
                for path in filepath:
                    output = subprocess.check_output(path, shell=True, errors=None, stdin=DEVNULL, stderr=DEVNULL)
                    version = output.decode('utf-8').strip().replace('Version=', '')
                    if version.find('.') != -1:
                        version = '.'.join(version.split('.')[:-1])
                        self._load_driver(version)
                        self._load_browser(headless)
                        break
                else:
                    raise Exception('Установите Google Chrome')
            except Exception as e:
                self._browser_wait = False
                raise BrowserException(e)
        finally:
            self._browser_wait = False

    def load_cookies(self, cookies_location, url=None):
        with open(cookies_location, 'rb') as cookiesfile:
            cookies = pickle.load(cookiesfile)
            self.browser.delete_all_cookies()
            self.browser.get("https://google.com" if url is None else url)
            for cookie in cookies:
                if isinstance(cookie.get('expiry'), float): 
                    cookie['expiry'] = int(cookie['expiry'])
                self.browser.add_cookie(cookie)

    def save_cookies(self, cookies_location, cookies=None):
        with open(cookies_location, 'wb') as filehandler:
            if cookies:
                pickle.dump(cookies, filehandler)
            else:
                pickle.dump(self.browser.get_cookies(), filehandler)

    def wait(self, path, path2='', timer=20, mode=By.XPATH):
        t = 0
        while True:
            try:        
                if t >= timer and timer != 0:
                    return False  
                try:
                    self.browser.find_element(mode, path)
                except:
                    self.browser.find_element(mode, path2)
                return True
            except Exception as e:
                if 'chrome not reachable' in str(e):
                    return False
                t += 1
                time.sleep(0.5)

    def exit(self):
        if self.browser:
            while self._browser_wait:
                time.sleep(1)
            try:
                self.browser.close()
            except Exception:
                pass
            try:
                self.browser.quit()
            except Exception:
                pass
            self.browser = None
        sessions.remove(self)


def clear():
    while sessions:
        sessions[0].exit()
