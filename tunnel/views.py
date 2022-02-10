# Create your views here.
import copy
import logging
import uuid

from django.http.response import Http404
from rest_framework import mixins
from rest_framework import status
from rest_framework import utils
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from . import utils
from .models import TunnelModel
from .serializers import RemoteSerializer
from .serializers import TunnelSerializer
from jupyterjsc_tunneling.decorators import request_decorator
from jupyterjsc_tunneling.permissions import HasGroupPermission
from jupyterjsc_tunneling.settings import LOGGER_NAME


log = logging.getLogger(LOGGER_NAME)


class TunnelViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = TunnelSerializer
    queryset = TunnelModel.objects.all()

    lookup_field = "startuuidcode"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def perform_create(self, serializer):
        data = copy.deepcopy(serializer.validated_data)
        data["uuidcode"] = self.request.query_params.dict().get(
            "uuidcode", uuid.uuid4().hex
        )
        try:
            utils.start_tunnel(alert_admins=True, raise_exception=True, **data)
            utils.k8s_svc("create", alert_admins=True, raise_exception=True, **data)
        except Exception as e:
            utils.stop_tunnel(alert_admins=False, raise_exception=False, **data)
            raise e

        return super().perform_create(serializer)

    def perform_destroy(self, instance):
        utils.stop_and_delete(
            alert_admins=True, raise_exception=False, **instance.__dict__
        )
        return super().perform_destroy(instance)

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
        data = copy.deepcopy(self.request.query_params.dict())
        if "uuidcode" not in data.keys():
            data["uuidcode"] = uuid.uuid4().hex
        utils.stop_remote(alert_admins=False, raise_exception=True, **data)

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
        serializer = self.get_serializer(data=request.query_params.dict())
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.validated_data, status=200)

    @request_decorator
    def delete(self, request, *args, **kwargs):
        self.perform_destroy()
        return Response(status=status.HTTP_204_NO_CONTENT)
