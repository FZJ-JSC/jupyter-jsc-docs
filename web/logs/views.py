# Create your views here.
import logging

from jupyterjsc_tunneling.decorators import request_decorator
from jupyterjsc_tunneling.permissions import HasGroupPermission
from jupyterjsc_tunneling.settings import LOGGER_NAME
from rest_framework import viewsets
from rest_framework.response import Response

from .models import HandlerModel
from .serializers import HandlerSerializer

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class HandlerViewSet(viewsets.ModelViewSet):
    serializer_class = HandlerSerializer
    queryset = HandlerModel.objects.all()
    lookup_field = "handler"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_logging"]


class LogTestViewSet(viewsets.GenericViewSet):
    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_logging"]

    @request_decorator
    def list(self, request, *args, **kwargs):
        log.trace("Trace")
        log.debug("Debug")
        log.info("Info")
        log.warning("Warn")
        log.error("Error")
        log.critical(
            "Critical",
            extra={"Extra1": "message1", "mesg": "msg1", "filename": "forbidden"},
        )
        return Response(status=200)
