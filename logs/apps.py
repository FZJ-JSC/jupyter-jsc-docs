import logging
import os

from django.apps import AppConfig

from jupyterjsc_tunneling.settings import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

from jupyterjsc_tunneling.decorators import current_logger_configuration_mem
from jupyterjsc_tunneling.settings import LOGGER_NAME
from logs.utils import create_logging_handler
from logs.utils import remove_logging_handler
import copy

from django.db.utils import OperationalError


class LogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logs"

    def start_logger(self):
        logging.addLevelName(5, "TRACE")

        def trace_func(self, message, *args, **kws):
            if self.isEnabledFor(5):
                # Yes, logger takes its '*args' as 'args'.
                self._log(5, message, args, **kws)

        logging.Logger.trace = trace_func
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

        if len(active_handler_dict) == 0 and len(current_logger_configuration_mem) == 0:
            active_handler_dict = {
                "stream": {
                    "formatter": "simple",
                    "level": 10,
                    "stream": "ext://sys.stdout",
                }
            }

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
            except OperationalError:
                pass
        return super().ready()
