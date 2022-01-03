import logging.handlers
import socket
import sys

from jsonformatter import JsonFormatter

from jupyterjsc_tunneling.settings import LOGGER_NAME

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


def create_logging_handler(handler_name, **kwargs):
    formatter_name = kwargs.pop("formatter")
    level = get_level(kwargs.pop("level"))
    # catch some special cases
    if handler_name == "stream":
        if kwargs["stream"] == "ext://sys.stdout":
            kwargs["stream"] = sys.stdout
        else:
            kwargs["stream"] = sys.stderr
    elif handler_name == "syslog":
        if kwargs.get("socktype", "") == "ext://socket.SOCK_STREAM":
            kwargs["socktype"] = socket.SOCK_STREAM
        else:
            kwargs["socktype"] = socket.SOCK_DGRAM
        kwargs["address"] = tuple(kwargs["address"])
    # Create handler, formatter, and add it
    handler = supported_handler_classes[handler_name](**kwargs)
    formatter = supported_formatter_classes[formatter_name](
        **supported_formatter_kwargs[formatter_name]
    )
    handler.name = handler_name
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)


def remove_logging_handler(handler_name):
    logger = logging.getLogger(LOGGER_NAME)
    logger_handlers = logger.handlers
    logger.handlers = [x for x in logger_handlers if x.name != handler_name]
