import logging

from django.apps import AppConfig

from jupyterjsc_tunneling.settings import LOGGER_NAME


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

    def ready(self):
        self.start_logger()
