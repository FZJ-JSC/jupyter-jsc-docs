import copy
import json
import logging
import os
import socket
import sys

from jsonformatter import JsonFormatter

from .settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


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
        "_state",
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
json_fmt = {
    "asctime": "asctime",
    "levelno": "levelno",
    "levelname": "levelname",
    "logger": LOGGER_NAME,
    "file": "pathname",
    "line": "lineno",
    "function": "funcName",
    "Message": "message",
}
simple_fmt = f"%(asctime)s logger={LOGGER_NAME} levelno=%(levelno)s levelname=%(levelname)s file=%(pathname)s line=%(lineno)d function=%(funcName)s : %(message)s"
supported_formatter_kwargs = {
    "json": {"fmt": json_fmt, "mix_extra": True},
    "simple": {"fmt": simple_fmt},
}


def update_extra_handlers(logging_config):
    if logging.getLevelName(5) != "TRACE":
        # First call
        # Remove default StreamHandler
        if len(log.handlers) > 0:
            log.removeHandler(log.handlers[0])

        # In trace will be sensitive information like tokens
        logging.addLevelName(5, "TRACE")

        def trace_func(self, message, *args, **kws):
            if self.isEnabledFor(5):
                # Yes, logger takes its '*args' as 'args'.
                self._log(5, message, args, **kws)

        logging.Logger.trace = trace_func
        log.setLevel(5)

    logger = logging.getLogger(LOGGER_NAME)
    logger_handlers = logger.handlers
    handler_names = [x.name for x in logger_handlers]

    for handler_name, handler_config in logging_config.items():
        if (not handler_config.get("enabled", False)) and handler_name in handler_names:
            # Handler was disabled, remove it
            logger.handlers = [x for x in logger_handlers if x.name != handler_name]
            logger.debug(f"Logging handler removed ({handler_name})")
        elif handler_config.get("enabled", False):
            # Recreate handlers which has changed their config
            configuration = copy.deepcopy(handler_config)

            # map some special values
            if handler_name == "stream":
                if configuration["stream"] == "ext://sys.stdout":
                    configuration["stream"] = sys.stdout
                elif configuration["stream"] == "ext://sys.stderr":
                    configuration["stream"] = sys.stderr
            elif handler_name == "syslog":
                if configuration["socktype"] == "ext://socket.SOCK_STREAM":
                    configuration["socktype"] = socket.SOCK_STREAM
                elif configuration["socktype"] == "ext://socket.SOCK_DGRAM":
                    configuration["socktype"] = socket.SOCK_DGRAM

            _ = configuration.pop("enabled")
            formatter_name = configuration.pop("formatter")
            level = get_level(configuration.pop("level"))
            none_keys = []
            for key, value in configuration.items():
                if value is None:
                    none_keys.append(key)
            for x in none_keys:
                _ = configuration.pop(x)

            # Create handler, formatter, and add it
            handler = supported_handler_classes[handler_name](**configuration)
            formatter = supported_formatter_classes[formatter_name](
                **supported_formatter_kwargs[formatter_name]
            )
            handler.name = handler_name
            handler.setLevel(level)
            handler.setFormatter(formatter)
            if handler_name in handler_names:
                # Remove previously added handler
                logger.handlers = [x for x in logger_handlers if x.name != handler_name]
            logger.addHandler(handler)

            if "filename" in configuration:
                # filename is already used in log.x(extra)
                configuration["file_name"] = configuration["filename"]
                del configuration["filename"]
            logger.debug(f"Logging handler added ({handler_name})", extra=configuration)
