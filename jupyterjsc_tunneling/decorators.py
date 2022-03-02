import copy
import logging
from datetime import datetime
from datetime import timedelta

from rest_framework.response import Response

from .settings import LOGGER_NAME
from logs.utils import create_logging_handler
from logs.utils import remove_logging_handler


log = logging.getLogger(LOGGER_NAME)

"""
We have to run this function at every request. If we're running 
multiple pods in a kubernetes cluster only one pod receives a logging
update. But this pod will change the database entries. So we check
on every request, if our current logging setup (in this specific pod) is
equal to the database.

Any hook / trigger at database updates would only be called on one pod.
Since logging is thread-safe, we cannot run an extra thread to update
handlers.
"""
current_logger_configuration_mem = {}


def request_decorator(func):
    def update_logging_handler(*args, **kwargs):
        global current_logger_configuration_mem
        from logs.models import HandlerModel

        logger = logging.getLogger(LOGGER_NAME)
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
            if e.__class__.__name__ == "TunnelException":
                details = {"error": e.args[0], "detailed_error": e.args[1]}
            else:
                details = {"error": "Unexpected Error", "detailed_error": str(e)}
            log.debug("Error Handling, return 500.", exc_info=True, extra=details)
            return Response(details, status=500)

    return catch_all_exceptions
