import copy
import json
import logging
import socket
import sys
import time

from jsonformatter import JsonFormatter

from .logging_classes import ExtraFormatter
from common.logger import LOGGER_NAME


def get_level(level_str):
    if type(level_str) == int:
        return level_str
    elif level_str.upper() in logging._nameToLevel.keys():
        return logging._nameToLevel[level_str.upper()]
    elif level_str.upper() == "TRACE":
        return 5
    elif level_str.upper().startswith() == "DEACTIVATE":
        return 99
    else:
        try:
            return int(level_str)
        except ValueError:
            pass
    raise NotImplementedError(f"{level_str} as level not supported.")


def create_logging_handler(handler_name, configuration_str):
    if type(configuration_str) == dict:
        configuration = configuration_str
    else:
        configuration = json.loads(configuration_str)
    handler = None
    if configuration["class"] == "logging.handlers.TimedRotatingFileHandler":
        filename = configuration["filename"]
        when = configuration["when"]
        backupCount = configuration["backupCount"]
        handler = logging.handlers.TimedRotatingFileHandler(
            filename, when=when, backupCount=backupCount
        )
    elif configuration["class"] == "logging.handlers.SMTPHandler":
        fromaddr = configuration["fromaddr"]
        mailhost = configuration["mailhost"]
        subject = configuration["subject"]
        toaddrs = configuration["toaddrs"]
        handler = logging.handlers.SMTPHandler(mailhost, fromaddr, toaddrs, subject)
    elif configuration["class"] == "logging.StreamHandler":
        if configuration["stream"] == "ext://sys.stdout":
            stream = sys.stdout
        else:
            stream = sys.stderr
        handler = logging.StreamHandler(stream=stream)
    elif configuration["class"] == "logging.handlers.SysLogHandler":
        address = tuple(configuration["address"])
        if configuration["socktype"] == "ext://socket.SOCK_STREAM":
            socktype = socket.SOCK_STREAM
        else:
            socktype = socket.SOCK_DGRAM
        handler = logging.handlers.SysLogHandler(address=address, socktype=socktype)
    else:
        raise NotImplementedError(f"{configuration['class']} not implemented.")
    if configuration["formatter"] == "json":
        formatter = JsonFormatter(
            '{"asctime": "asctime", "levelno": "levelno", "levelname": "levelname", "logger": "name", "file": "pathname", "line": "lineno", "function": "funcName", "Message": "message"}',
            mix_extra=True,
        )
    elif configuration["formatter"] == "simple":
        formatter = ExtraFormatter(
            "%(asctime)s logger=%(name)s levelno=%(levelno)s levelname=%(levelname)s file=%(pathname)s line=%(lineno)d function=%(funcName)s : %(message)s"
        )
    else:
        raise NotImplementedError(f"{configuration['formatter']} not implemented.")
    handler.name = handler_name
    handler.setLevel(get_level(configuration["level"]))
    handler.setFormatter(formatter)
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)


def remove_logging_handler(handler_name):
    logger = logging.getLogger(LOGGER_NAME)
    logger_handlers = logger.handlers
    logger.handlers = [x for x in logger_handlers if x.name != handler_name]
