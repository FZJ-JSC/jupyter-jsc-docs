# Create your views here.
import copy
import logging
import uuid

from jupyterjsc_tunneling.decorators import request_decorator
from jupyterjsc_tunneling.permissions import HasGroupPermission
from jupyterjsc_tunneling.settings import LOGGER_NAME
from rest_framework import mixins
from rest_framework import status
from rest_framework import utils
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from . import utils
from .models import TunnelModel
from .serializers import RemoteSerializer
from .serializers import TunnelSerializer


log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class RestartViewSet(GenericAPIView):
    queryset_tunnel = TunnelModel.objects.all()
    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice_restart"]

    @request_decorator
    def post(self, request, *args, **kwargs):
        hostname = request.data.get("hostname", None)
        if not hostname:
            raise ValidationError("Hostname missing")
        custom_headers = utils.get_custom_headers(self.request._request.META)
        log.info(
            f"Restart for all tunnels requested for {hostname}", extra=custom_headers
        )
        tunnels = self.queryset_tunnel.filter(hostname=hostname).all()
        for tunnel in tunnels:
            kwargs = {}
            for key, value in tunnel.__dict__.items():
                if key not in ["date", "_state"]:
                    kwargs[key] = copy.deepcopy(value)

            kwargs.update(custom_headers)
            log.debug(f"Restart tunnel for {hostname}", extra=kwargs)
            utils.stop_tunnel(alert_admins=True, raise_exception=False, **kwargs)
            utils.start_tunnel(alert_admins=True, raise_exception=False, **kwargs)

        custom_headers["hostname"] = hostname
        utils.stop_remote(alert_admins=True, raise_exception=False, **custom_headers)
        utils.start_remote(alert_admins=True, raise_exception=False, **custom_headers)
        return Response(status=200)


class RemoteCheckViewSet(GenericAPIView):
    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice_remote_check"]

    @request_decorator
    def get(self, request, *args, **kwargs):
        utils.start_remote_from_config_file(
            **utils.get_custom_headers(self.request._request.META)
        )
        return Response(status=200)


class TunnelViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = TunnelSerializer
    queryset = TunnelModel.objects.all()

    lookup_field = "servername"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def perform_create(self, serializer):
        data = copy.deepcopy(serializer.validated_data)
        data["uuidcode"] = data["servername"]
        data.update(utils.get_custom_headers(self.request._request.META))
        try:
            utils.start_tunnel(alert_admins=True, raise_exception=True, **data)
            utils.k8s_svc("create", alert_admins=True, raise_exception=True, **data)
        except Exception as e:
            utils.stop_tunnel(alert_admins=False, raise_exception=False, **data)
            raise e

        return super().perform_create(serializer)

    def perform_destroy(self, instance):
        data = {}
        for key, value in instance.__dict__.items():
            if key not in ["date", "_state"]:
                data[key] = copy.deepcopy(value)
        data.update(utils.get_custom_headers(self.request._request.META))
        utils.stop_and_delete(alert_admins=True, raise_exception=False, **data)
        return super().perform_destroy(instance)

    def get_object(self):
        try:
            return super().get_object()
        except TunnelModel.MultipleObjectsReturned:
            log.warning("Multiple Objects found. Keep only latest one")
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            lookup_kwargs = {lookup_url_kwarg: self.kwargs[lookup_url_kwarg]}
            models = self.get_queryset().filter(**lookup_kwargs).all()
            ids = [x.id for x in models]
            keep_id = max(ids)
            for model in models:
                if not model.id == keep_id:
                    self.perform_destroy(model)
            return super().get_object()

    @request_decorator
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @request_decorator
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @request_decorator
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @request_decorator
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class RemoteViewSet(GenericAPIView):
    serializer_class = RemoteSerializer
    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def perform_create(self, data):
        utils.start_remote(alert_admins=True, raise_exception=True, **data)

    def perform_destroy(self):
        custom_headers = utils.get_custom_headers(self.request._request.META)
        utils.stop_remote(alert_admins=False, raise_exception=True, **custom_headers)

    @request_decorator
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = copy.deepcopy(serializer.validated_data)
        self.perform_create(data)
        # If it wouldn't be running, perform_create would have thrown an exception
        data["running"] = True
        return Response(data=data, status=200)

    @request_decorator
    def get(self, request, *args, **kwargs):
        custom_headers = utils.get_custom_headers(self.request._request.META)
        serializer = self.get_serializer(data=custom_headers)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.validated_data, status=200)

    @request_decorator
    def delete(self, request, *args, **kwargs):
        self.perform_destroy()
        return Response(status=status.HTTP_204_NO_CONTENT)
