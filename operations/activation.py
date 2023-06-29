# -*- coding: utf-8 -*-
import json
import logging
import time

import pandas as pd
import requests

from operations.base import BaseOperation

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s",
    filename="activation.log",
    level=logging.DEBUG,
)


class Activation(BaseOperation):
    def read_data(self):
        logging.debug("Read input data")
        self.naming = {
            "path": self.window.path_input_4.text(),
            "sheet_name": self.window.sheet_input_4.text(),
            "id": self.window.id_input_4.text(),
            "date": self.window.date_input_4.text(),
            "time": self.window.time_input_4.text(),
            "extension": "Extension",
        }
        logging.info("Read input data DONE")

        logging.debug("Data validation")
        if "" in (
            self.naming["path"],
            self.naming["sheet_name"],
            self.naming["id"],
            self.naming["date"],
            self.naming["time"],
        ):
            self.thread.output_signal.emit("Заполните все поля", self.output)
            logging.warning("Data validation FAILED")
            return False
        else:
            logging.info("Data validation DONE")
            return True

    def activation_excel(self):
        logging.debug("Reading Excel file")
        df = pd.read_excel(
            self.naming["path"],
            sheet_name=self.naming["sheet_name"],
            keep_default_na=False,
            converters={self.naming["id"]: str},
        )
        logging.info("Reading Excel file DONE")

        logging.debug("Data filtering")
        today = pd.Timestamp.today().date()
        now = pd.Timestamp.now().time()
        for row in df.iterrows():
            if not row[1][self.naming["id"]]:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit("Не найден ID", self.output)
            elif not row[1][[self.naming["date"], self.naming["time"]]].all():
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming["id"]] + " - Заполните все столбцы", self.output)
            elif row[1][self.naming["date"]] < today or row[1][self.naming["time"]] < now:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(
                    row[1][self.naming["id"]] + " - Реклама не активированна, опоздание по времени",
                    self.output,
                )
        df.reset_index(drop=True, inplace=True)
        logging.info("Data filtering DONE")

        df[self.naming["extension"]] = 0
        return df

    def activation_report(self, df, row, status, sound=False, report=None):
        df.drop(index=row[0], inplace=True)
        if sound:
            self.window.play_sound("error")
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

            logging.debug("Start activation")
            self.thread.output_signal.emit("Активация запущена", self.output)
            while not data.empty:
                today = pd.Timestamp.today().to_datetime64()
                now = pd.Timestamp.now().time()
                df = data[(data[self.naming["date"]] <= today) & (data[self.naming["time"]] <= now)]
                for row in df.iterrows():
                    logging.debug(f"{row[1][self.naming['id']]} - Advertisement activation")
                    status = self.activate(df, row)
                    if status == 200:
                        self.activation_report(df, row, "Объявление активировано")
                        logging.info(f"{row[1][self.naming['id']]} - Advertisement activation DONE")
                    elif status == 404:
                        self.activation_report(df, row, "Объявление не найдено", sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Advertisement not found")
                    elif status == 408:
                        timestamp = pd.Timestamp(
                            row[1][self.naming["date"]].year,
                            row[1][self.naming["date"]].month,
                            row[1][self.naming["date"]].day,
                            row[1][self.naming["time"]].hour,
                            row[1][self.naming["time"]].minute,
                        ) + pd.Timedelta(minutes=2)
                        df.loc[row[0], [self.naming["date"], self.naming["time"]]] = [
                            timestamp.date(),  # to_datetime64
                            timestamp.time(),
                        ]
                        self.thread.output_signal.emit(
                            f"{row[1][self.naming['id']]} - Активация перенесена на 2 минуты",
                            self.output,
                        )
                        logging.warning(f"{row[1][self.naming['id']]} - Activation delay")
                    elif status == 409:
                        self.activation_report(df, row, "Объявление уже активировано", sound=True)
                        logging.error(f"{row[1][self.naming['id']]} - Advertisement already activated")
                    else:
                        self.activation_report(df, row, status, sound=True, report="Activation")
                        logging.critical(f"{row[1][self.naming['id']]} - {status}")
            self.thread.output_signal.emit("Активация выполненна", self.output)
            logging.info("Activation DONE")
        except Exception as e:
            self.window.report(str(e), "Activation")
            self.thread.output_signal.emit("Активация остановлена, ошибка", self.output)
            self.window.report("Активация остановлена, ошибка")
            logging.critical(str(e))
        finally:
            self.session.exit()
            logging.debug("End activation")

    def activate(self, df, row, refresh=True):
        try:
            with open("data/tokens.json", "r") as file:
                tokens = json.loads(file.read())

            headers = {
                "authority": "production-graphql.eu-sharedservices.olxcdn.com",
                "accept": "*/*",
                "accept-language": "ru",
                "authorization": f"Bearer {tokens['access_token']}",
                "content-type": "application/json",
                "origin": "https://www.olx.ua",
                "referer": "https://www.olx.ua/",
                "sec-ch-ua": '"Opera";v="99", "Chromium";v="113", "Not-A.Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "site": "olxua",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 OPR/99.0.0.0",
                "x-client": "DESKTOP",
                "x-fingerprint": "MTI1NzY4MzI5MTsxMjswOzA7MDsxOzA7MDswOzA7MDsxOzE7MTsxOzE7MTsxOzE7MTsxOzE7MTsxOzE7MDsxOzE7MTswOzA7MTsxOzE7MTsxOzE7MTsxOzE7MTswOzE7MTswOzE7MTsxOzA7MDswOzA7MDswOzE7MDsxOzE7MDswOzA7MTswOzA7MTsxOzA7MTsxOzE7MTswOzE7MDsxOTA5NzQ2NTY3OzI7MjsyOzI7MjsyOzU7Mjg0ODAwNjQxODsxMzU3MDQxNzM4OzE7MTsxOzE7MTsxOzE7MTsxOzE7MTsxOzE7MTsxOzE7MTswOzA7MDszNTYzNjM2Njc7MzQ2OTMwNjU1MTszNDg2MzEyNzI0Ozc4NTI0NzAyOTsxMDA1MzAxMjAzOzE5MjA7MTA4MDsyNDsyNDsxODA7MTIwOzE4MDsxMjA7MTgwOzEyMDsxODA7MTIwOzE4MDsxMjA7MTgwOzEyMDsxODA7MTIwOzE4MDsxMjA7MTgwOzEyMDsxODA7MTIwOzA7MDsw",
                "x-userispro": "true",
            }

            payload = {
                "query": "mutation UpdateAd($adId: Int, $action: B2CAction) {\n    b2c {\n        updateAd(adId: $adId, action: $action) {\n            adId\n            status\n            message\n        }\n    }\n}\n",
                "variables": {
                    "adId": row[1][self.naming["id"]],
                    "action": "ACTIVATE",
                },
            }

            response = requests.post(
                "https://production-graphql.eu-sharedservices.olxcdn.com/graphql",
                headers=headers,
                json=payload,
            ).json()

            if response.get("errors"):
                if response["errors"]["message"] == "401: Unauthorized" and refresh:
                    self.refresh()
                    return self.activate(df, row, False)
                else:
                    return str(response)

            if response["data"]["b2c"]["updateAd"]["status"] == "SUCCESS":
                return 200
            elif response["data"]["b2c"]["updateAd"]["status"] == "FAILED":
                return 404
            elif response["data"]["b2c"]["updateAd"]["status"] == "ERROR_VALIDATION":
                if row[1][self.naming["extension"]] < 5:
                    df.loc[row[0], self.naming["extension"]] += 1
                    return 408
                else:
                    return 409
            else:
                return str(response)
        except Exception as e:
            return str(e)
