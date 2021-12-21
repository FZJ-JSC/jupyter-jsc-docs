# Create your views here.
import logging

from rest_framework import viewsets
from rest_framework.response import Response

from ..models.logs_models import HandlerModel
from ..serializers.logs_serializer import HandlerSerializer
from common.decorators import request_decorator
from common.logger import LOGGER_NAME
from common.permissions import HasGroupPermission

log = logging.getLogger(LOGGER_NAME)


class HandlerViewSet(viewsets.ModelViewSet):
    serializer_class = HandlerSerializer
    queryset = HandlerModel.objects.all()
    lookup_field = "handler"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_logging"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


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
        log.critical("Critical", extra={"Extra1": "message1", "mesg": "msg1"})
        return Response(status=200)
