import logging
import os

import yaml
from rest_framework.response import Response

from .logs import update_extra_handlers
from .settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"

"""
Check logging config update at each request.
"""
_logging_config_cache = {}
_logging_config_last_update = 0
_logging_config_file = os.environ.get("LOGGING_CONFIG_PATH")


def request_decorator(func):
    def update_logging_handler(*args, **kwargs):
        global _logging_config_cache
        global _logging_config_last_update

        # Only update logging_config, if it has changed on disk
        try:
            last_change = os.path.getmtime(_logging_config_file)
            if last_change > _logging_config_last_update:
                log.debug("Load logging config file.")
                with open(_logging_config_file, "r") as f:
                    ret = yaml.full_load(f)
                _logging_config_last_update = last_change
                _logging_config_cache = ret
                log.debug("Update Logger")
                update_extra_handlers(_logging_config_cache)
        except:
            log.exception("Could not load logging config file")
        return func(*args, **kwargs)

    def catch_all_exceptions(*args, **kwargs):
        try:
            return update_logging_handler(*args, **kwargs)
        except Exception as e:
            if hasattr(e, "__module__") and e.__module__ in [
                "django.http.response",
                "rest_framework.exceptions",
            ]:
                raise e
            if e.__class__.__name__ == "TunnelExceptionError":
                details = {"error": e.args[0], "detailed_error": e.args[1]}
            else:
                details = {"error": "Unexpected Error", "detailed_error": str(e)}
            log.debug("Error Handling, return 500.", exc_info=True, extra=details)
            return Response(details, status=500)

    return catch_all_exceptions
