import logging

# We might want to log forbidden extra keywords like "filename".
# Instead of raising an exception, we just alter the keyword
class ExtraLoggerClass(logging.Logger):
    def trace(self, message, *args, **kws):
        if self.isEnabledFor(5):
            # Yes, logger takes its '*args' as 'args'.
            self._log(5, message, args, **kws)

    def makeRecord(
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        rv = logging._logRecordFactory(
            name, level, fn, lno, msg, args, exc_info, func, sinfo
        )
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    rv.__dict__[f"{key}_extra"] = extra[key]
                else:
                    rv.__dict__[key] = extra[key]
        return rv


logging.setLoggerClass(ExtraLoggerClass)

import copy
import os

from django.apps import AppConfig
from jupyterjsc_tunneling.decorators import current_logger_configuration_mem
from jupyterjsc_tunneling.settings import LOGGER_NAME
from logs.utils import create_logging_handler
from logs.utils import remove_logging_handler

logger = logging.getLogger(LOGGER_NAME)
assert logger.__class__.__name__ == "ExtraLoggerClass"


class LogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logs"

    def start_logger(self):
        logging.addLevelName(5, "TRACE")
        logging.getLogger(LOGGER_NAME).setLevel(5)
        logging.getLogger(LOGGER_NAME).propagate = False
        logging.getLogger().setLevel(40)
        logging.getLogger().propagate = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_handler(self):
        from .models import HandlerModel

        global current_logger_configuration_mem

        active_handler = HandlerModel.objects.all()
        active_handler_dict = {x.handler: x.configuration for x in active_handler}

        if active_handler_dict != current_logger_configuration_mem:
            logger_handlers = logger.handlers
            logger.handlers = [
                handler
                for handler in logger_handlers
                if handler.name in active_handler_dict.keys()
            ]
            for name, configuration in active_handler_dict.items():
                if configuration != current_logger_configuration_mem.get(name, {}):
                    remove_logging_handler(name)
                    create_logging_handler(name, **configuration)
            current_logger_configuration_mem = copy.deepcopy(active_handler_dict)
        logger.info("logging handler setup done", extra={"uuidcode": "StartUp"})

    def ready(self):
        if os.environ.get("UWSGI_START", "false").lower() == "true":
            self.start_logger()
            try:
                self.add_handler()
            except:
                logger.exception("Unexpected error during startup")
            # < VERSION > will be replaced by actual value in CI pipeline
            logger.info(
                "Start Tunnel Service version <VERSION>", extra={"uuidcode": "StartUp"}
            )
        return super().ready()
