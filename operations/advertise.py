# -*- coding: utf-8 -*-
import json
import time
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING

import pandas as pd
import requests

from operations.base import BaseOperation


class Advertise(BaseOperation):
    def read_data(self):
        self.log("Read input data", DEBUG)
        self.naming = {
            "path": self.window.path_input_1.text(),
            "sheet_name": self.window.sheet_input_1.text(),
            "id": self.window.id_input_1.text(),
            "date": self.window.date_input_1.text(),
            "time": self.window.time_input_1.text(),
            "tariff": self.window.tariff_input_1.text(),
            "service": self.window.service_input_1.text(),
            "extension": "Extension",
        }
        self.log("Read input data DONE", INFO)

        self.log("Data validation", DEBUG)
        if "" in (
            self.naming["path"],
            self.naming["sheet_name"],
            self.naming["id"],
            self.naming["date"],
            self.naming["time"],
            self.naming["tariff"],
            self.naming["service"],
        ):
            self.thread.output_signal.emit("Заполните все поля", self.output)
            self.log("Data validation FAILED", WARNING)
            return False
        else:
            self.log("Data validation DONE", INFO)
            return True

    def advertise_excel(self):
        self.log("Reading Excel file", DEBUG)
        df = pd.read_excel(
            self.naming["path"],
            sheet_name=self.naming["sheet_name"],
            keep_default_na=False,
            converters={self.naming["id"]: str},
        )
        self.log("Reading Excel file DONE", INFO)

        self.log("Data filtering", DEBUG)
        today = pd.Timestamp.today().date()
        now = pd.Timestamp.now().time()
        for row in df.iterrows():
            if not row[1][self.naming["id"]]:
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit("Не найден ID", self.output)
            elif not row[1][[self.naming["date"], self.naming["time"]]].all():
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming["id"]] + " - Заполните все столбцы", self.output)
            elif not row[1][[self.naming["tariff"], self.naming["service"]]].any():
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(row[1][self.naming["id"]] + " - Не выбран тариф", self.output)
            elif row[1][self.naming["date"]] < today or (
                row[1][self.naming["date"]] == today and row[1][self.naming["time"]] < now
            ):
                df.drop(index=row[0], inplace=True)
                self.thread.output_signal.emit(
                    row[1][self.naming["id"]] + " - Реклама не оплачена, опоздание по времени",
                    self.output,
                )
        df.reset_index(drop=True, inplace=True)
        self.log("Data filtering DONE", INFO)

        df[self.naming["extension"]] = 0
        return df

    def advertise_report(self, data, row, status, sound=False, report=None):
        data.drop(index=row[0], inplace=True)
        if sound:
            self.window.play_sound("error")
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

            self.log("Get Excel data", DEBUG)
            data = self.advertise_excel()
            if data.empty:
                self.log("Get Excel data FAILED", WARNING)
                return None
            self.log("Get Excel data DONE", WARNING)

            self.log("Start advertising", DEBUG)
            self.thread.output_signal.emit("Реклама запущена", self.output)
            while not data.empty and not self.thread.stop_flag:
                today = pd.Timestamp.today().normalize().to_datetime64()
                now = pd.Timestamp.now().time()
                df = data[(data[self.naming["date"]] <= today) & (data[self.naming["time"]] <= now)]
                for row in df.iterrows():
                    if self.thread.stop_flag:
                        break
                    self.log(f"{row[1][self.naming['id']]} - Advertising payment", DEBUG)
                    status = self.payment(data, row)
                    if status == 200:
                        self.advertise_report(data, row, "Реклама оплачена")
                        self.log(f"{row[1][self.naming['id']]} - Advertising payment DONE", INFO)
                    elif status == 202:
                        self.advertise_report(
                            data,
                            row,
                            "Срок действия услуги превышает срок размещения объявления",
                            sound=True,
                        )
                        self.log(f"{row[1][self.naming['id']]} - Posting period exceeded", WARNING)
                    elif status == 402:
                        self.advertise_report(data, row, "Реклама не оплачена, недостаточно средств", sound=True)
                        self.log(f"{row[1][self.naming['id']]} - Insufficient funds", ERROR)
                    elif status == 403:
                        self.advertise_report(data, row, "Реклама не оплачена, не найден тариф", sound=True)
                        self.log(f"{row[1][self.naming['id']]} - Tariff not found", ERROR)
                    elif status == 408:
                        timestamp = pd.Timestamp(
                            row[1][self.naming["date"]].year,
                            row[1][self.naming["date"]].month,
                            row[1][self.naming["date"]].day,
                            row[1][self.naming["time"]].hour,
                            row[1][self.naming["time"]].minute,
                        ) + pd.Timedelta(minutes=2)
                        data.loc[row[0], [self.naming["date"], self.naming["time"]]] = [
                            timestamp.normalize(),
                            timestamp.time(),
                        ]
                        self.thread.output_signal.emit(
                            f"{row[1][self.naming['id']]} - Оплата рекламы перенесена на 2 минуты",
                            self.output,
                        )
                        self.log(f"{row[1][self.naming['id']]} - Payment delay", WARNING)
                    elif status == 409:
                        self.advertise_report(data, row, "Реклама уже оплачена", sound=True)
                        self.log(f"{row[1][self.naming['id']]} - Advertisement already paid", ERROR)
                    else:
                        self.advertise_report(data, row, status, sound=True, report="Payment")
                        self.log(f"{row[1][self.naming['id']]} - {status}", CRITICAL)
                    time.sleep(10)
                time.sleep(1)
            self.thread.output_signal.emit("Все объявления прорекламированы", self.output)
            self.log("Advertising DONE", INFO)
        except Exception as e:
            self.window.report(str(e), "Advertise")
            self.thread.output_signal.emit("Реклама остановлена, ошибка", self.output)
            self.window.report("Реклама остановлена, ошибка")
            self.log(str(e), CRITICAL)
        finally:
            self.log("End advertising", DEBUG)

    def is_active(self, token, ad_id):
        headers = {
            "authority": "production-graphql.eu-sharedservices.olxcdn.com",
            "accept": "*/*",
            "accept-language": "ru",
            "authorization": f"Bearer {token}",
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
            "query": "query Inventory(\n    $limit: Int\n    $offset: Int\n    $filters: B2CAdsFiltersInput\n    $sorting: B2CAdSortingInput\n    $isActiveAds: Boolean!\n    $isDesktop: Boolean!\n) {\n    b2c {\n        ads(\n            limit: $limit\n            offset: $offset\n            filters: $filters\n            sorting: $sorting\n        ) {\n            totalCount\n            items {\n                activatedAt\n                canRefreshForFree\n                categoryId\n                currency\n                editable\n                id\n                isJob\n                isCalendarEnabled\n                isPartnerAd\n                photos\n                price\n                priceType\n                status\n                title\n                validTo\n                autoReposting {\n                    isSuccess\n                    message\n                }\n                categoryLevels {\n                    id\n                    name\n                    level\n                }\n                delivery {\n                    hasDelivery\n                    courier {\n                        isAvailable\n                        isEnabled\n                        ctt {\n                            isEnabled\n                            url\n                        }\n                    }\n                    rock {\n                        isEligible\n                        isManageable\n                    }\n                }\n                messageCounters {\n                    total\n                    new\n                }\n                refreshPrice {\n                    value\n                    currencySymbol\n                }\n                salario {\n                    value\n                    type\n                }\n                salary {\n                    valueFrom\n                    valueTo\n                    currency\n                    negotiable\n                    type\n                }\n                stats {\n                    views\n                    observed\n                    phones\n                    status\n                }\n                vases {\n                    type\n                    name\n                    validTo\n                    bundleName\n                    plannedRefreshes\n                }\n                vasRecommendation @include(if: $isActiveAds) {\n                    id\n                    type\n                    maximalPercentageViewUplift\n                    visibility\n                }\n                ... @skip(if: $isDesktop) {\n                    ... @include(if: $isActiveAds) {\n                        daysToExpire\n                        reposting\n                    }\n                }\n                ... @include(if: $isDesktop) {\n                    categories\n                    daysToExpire\n                    isRecommended\n                    lastRefreshAt\n                    reposting\n                    sku\n                    location {\n                        name\n                    }\n                }\n            }\n        }\n    }\n}\n",
            "variables": {
                "limit": 50,
                "offset": 0,
                "filters": {
                    "query": ad_id,
                    "status": "ACTIVE",
                },
                "sorting": {
                    "field": "createdAt",
                    "direction": "desc",
                },
                "isDesktop": True,
                "isActiveAds": True,
            },
        }

        response = requests.post(
            "https://production-graphql.eu-sharedservices.olxcdn.com/graphql",
            headers=headers,
            json=payload,
        ).json()
        self.log(f"Response: {response}", DEBUG)

        if response["data"]["b2c"]["ads"]["items"]:
            return True
        else:
            return False

    def payment(self, data, row, refresh=True):
        try:
            with open("data/tokens.json", "r") as file:
                tokens = json.loads(file.read())

            if row[1][self.naming["tariff"]]:
                if row[1][self.naming["tariff"]].find("Легкий старт") != -1:
                    tariff = "bundle_premium"
                elif row[1][self.naming["tariff"]].find("Быстрая продажа") != -1:
                    tariff = "bundle_premium"
                elif row[1][self.naming["tariff"]].find("Турбо продажа") != -1:
                    tariff = "bundle_premium"
                else:
                    return 403

            # if row[1][self.naming["service"]]:
            #     if row[1][self.naming["service"]].find("7 поднятий в верх списка") != -1:
            #         tariff = "bundle_premium"
            #     elif row[1][self.naming["service"]].find("VIP-объявление на 7 дней") != -1:
            #         tariff = "bundle_premium"
            #     elif row[1][self.naming["service"]].find("Топ-объявление на 7 дней") != -1:
            #         tariff = "bundle_premium"
            #     elif row[1][self.naming["service"]].find("Топ-объявление на 30 дней") != -1:
            #         tariff = "bundle_premium"
            #     else:
            #         return 403

            headers = {
                "authority": "www.olx.ua",
                "accept": "*/*",
                "accept-language": "ru",
                "authorization": f"Bearer {tokens['access_token']}",
                "content-type": "application/json",
                "origin": "https://www.olx.ua",
                "sec-ch-ua": '"Opera";v="99", "Chromium";v="113", "Not-A.Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 OPR/99.0.0.0",
                "x-client": "DESKTOP",
                "x-device-id": "8acd8772-e5bc-4066-bbd3-a4130726cfd0",
                "x-fingerprint": "fbdc4f53959cdb4a0ca0f7f0d089ca8a00ab77cc9433c497f1625c5c241a92a96255da10575393646255da105753936456b16d11aecc818682e4cda99633e224801d6b5073f992cf6255da10575393646255da105753936429b755643a58ca1b1aefb6d01788d83ee631c3c89377a0bb2601616aab71baecef069f2845625c9400ab77cc9433c497ef069f2845625c946255da10575393641623446252ae107826718a2feab8d0854c900da77a01aaf0061ced26da634318745ddd797fe8df60a8e06d4216f6691883bb1eb95319dd523fef60c9cf99daee3fef60c9cf99daee308e012c59cf7bddb497a357830277b80e237be963e4974ea1173d4df7b0c2973a4962d8c4406b9abdb8b1c784cc3aca42c4385be78445c39c5fc99f16cb2f54525fa71314aa02ef5b9640095b98711caa89f99d0a9270552bfcc98a9c5ab9543e54b784133872573e54b784133872573e54b784133872573e54b784133872573e54b784133872573e54b784133872573e54b784133872573e54b784133872573e54b78413387257aeda811d51584ead",
                "x-platform-type": "mobile-html5",
            }

            payload = {
                "provider": "account",
                "products": [
                    {
                        "code": tariff,
                        "ad_id": row[1][self.naming["id"]],
                        "zone_id": None,
                    },
                ],
                "promo": 0,
                "return": {
                    "url_template": f"https://www.olx.ua/purchase/confirmation/?transaction-id=[TRANSACTION_ID]&ad-id={row[1][self.naming['id']]}&bs=olx_pro_listing",
                },
            }

            response = requests.post("https://www.olx.ua/api/v1/transaction/", headers=headers, json=payload)
            response_data = response.json()

            if response.status_code == 401:
                if refresh:
                    self.refresh()
                    return self.payment(data, row, False)
                else:
                    return str(response_data)

            if response_data["action"] == "success":
                if self.is_active(tokens["access_token"], row[1][self.naming["id"]]):
                    return 200
                else:
                    return 202
            elif response_data["action"] == "insufficient_funds":
                return 402
            # elif False:
            #     if row[1][self.naming['extension']] < 5:
            #         data.loc[row[0], self.naming['extension']] += 1
            #         return 408
            #     else:
            #         return 409
            else:
                return str(response_data)
        except Exception as e:
            return str(e)
