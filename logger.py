# -*- coding: utf-8 -*-
import logging

logging.basicConfig(
    filename="logs.log",
    filemode='a',
    format="%(asctime)s %(levelname)s:%(message)s",
    level=logging.DEBUG,
)


class LogMixin:
    @classmethod
    def log(cls,  message: str, level=logging.DEBUG):
        logging.log(level, f"{cls.__name__}: {message}")
