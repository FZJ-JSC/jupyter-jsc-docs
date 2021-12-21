import logging


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
