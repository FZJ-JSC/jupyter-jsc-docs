import copy
import logging.handlers
import socket
import sys

from jsonformatter import JsonFormatter
from jupyterjsc_tunneling.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)

"""
This class allows us to log with extra arguments
log.info("message", extra={"key1": "value1", "key2": "value2"})
"""


class ExtraFormatter(logging.Formatter):
    dummy = logging.LogRecord(None, None, None, None, None, None, None)
    ignored_extras = [
        "args",
        "asctime",
        "created",
        "exc_info",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    ]

    def format(self, record):
        extra_txt = ""
        for k, v in record.__dict__.items():
            if k not in self.dummy.__dict__ and k not in self.ignored_extras:
                extra_txt += " --- {}={}".format(k, v)
        message = super().format(record)
        return message + extra_txt


# Translate level to int
def get_level(level_str):
    if type(level_str) == int:
        return level_str
    elif level_str.upper() in logging._nameToLevel.keys():
        return logging._nameToLevel[level_str.upper()]
    elif level_str.upper() == "TRACE":
        return 5
    elif level_str.upper().startswith("DEACTIVATE"):
        return 99
    else:
        try:
            return int(level_str)
        except ValueError:
            pass
    raise NotImplementedError(f"{level_str} as level not supported.")


# supported classes
supported_handler_classes = {
    "stream": logging.StreamHandler,
    "file": logging.handlers.TimedRotatingFileHandler,
    "smtp": logging.handlers.SMTPHandler,
    "syslog": logging.handlers.SysLogHandler,
}

# supported formatters and their arguments
supported_formatter_classes = {"json": JsonFormatter, "simple": ExtraFormatter}
json_fmt = '{"asctime": "asctime", "levelno": "levelno", "levelname": "levelname", "logger": "name", "file": "pathname", "line": "lineno", "function": "funcName", "Message": "message"}'
simple_fmt = "%(asctime)s logger=%(name)s levelno=%(levelno)s levelname=%(levelname)s file=%(pathname)s line=%(lineno)d function=%(funcName)s : %(message)s"
supported_formatter_kwargs = {
    "json": {"fmt": json_fmt, "mix_extra": True},
    "simple": {"fmt": simple_fmt},
}


def create_logging_handler(handler_name, **configuration):
    configuration_logs = {"configuration": str(configuration)}
    formatter_name = configuration.pop("formatter")
    level = get_level(configuration.pop("level"))

    # catch some special cases
    for key, value in configuration.items():
        if key == "stream":
            if value == "ext://sys.stdout":
                configuration["stream"] = sys.stdout
            elif value == "ext://sys.stderr":
                configuration["stream"] = sys.stderr
        elif key == "socktype":
            if value == "ext://socket.SOCK_STREAM":
                configuration["socktype"] = socket.SOCK_STREAM
            elif value == "ext://socket.SOCK_DGRAM":
                configuration["socktype"] = socket.SOCK_DGRAM
        elif key == "address":
            configuration["address"] = tuple(value)

    # Create handler, formatter, and add it
    handler = supported_handler_classes[handler_name](**configuration)
    formatter = supported_formatter_classes[formatter_name](
        **supported_formatter_kwargs[formatter_name]
    )
    handler.name = handler_name
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    log.debug(f"Logging handler added ({handler_name})", extra=configuration_logs)


def remove_logging_handler(handler_name):
    logger = logging.getLogger(LOGGER_NAME)
    logger_handlers = logger.handlers
    logger.handlers = [x for x in logger_handlers if x.name != handler_name]


default_configurations = {
    "stream": {"formatter": "simple", "level": 10, "stream": "ext://sys.stdout"},
    "file": {
        "formatter": "simple",
        "level": 10,
        "filename": "/tmp/file.log",
        "when": "midnight",
        "backupCount": 7,
    },
    "smtp": {
        "formatter": "simple",
        "level": 10,
        "mailhost": "",
        "fromaddr": "",
        "toaddrs": [],
        "subject": "",
    },
    "syslog": {
        "formatter": "json",
        "level": 10,
        "address": ["127.0.0.1", 514],
        "socktype": "ext://socket.SOCK_STREAM",
    },
}
