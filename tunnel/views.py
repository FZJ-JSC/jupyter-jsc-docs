# Create your views here.
import copy
import logging

from django.http.response import Http404
from rest_framework import status
from rest_framework import utils
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from . import utils
from .models import RemoteModel
from .models import TunnelModel
from .serializers import RemoteSerializer
from .serializers import TunnelSerializer
from jupyterjsc_tunneling.decorators import request_decorator
from jupyterjsc_tunneling.permissions import HasGroupPermission
from jupyterjsc_tunneling.settings import LOGGER_NAME

log = logging.getLogger(LOGGER_NAME)


class TunnelViewSet(viewsets.ModelViewSet):
    serializer_class = TunnelSerializer
    queryset = TunnelModel.objects.all()

    lookup_field = "backend_id"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def get_kwargs(self, instance=None):
        if instance:
            kwargs = {
                "backend_id": instance.backend_id,
                "hostname": instance.hostname,
                "local_port": instance.local_port,
                "target_node": instance.target_node,
                "target_port": instance.target_port,
            }
        else:
            if type(self.request.data) != dict:
                kwargs = {
                    "backend_id": self.request.data["backend_id"],
                    "hostname": self.request.data["hostname"],
                    "target_node": self.request.data["target_node"],
                    "target_port": self.request.data["target_port"],
                }
            else:
                kwargs = copy.deepcopy(self.request.data)
        kwargs["uuidcode"] = self.request.query_params.get("uuidcode", "no-uuidcode")
        return kwargs

    @request_decorator
    def create(self, request, *args, **kwargs):
        request_data = self.get_kwargs()
        request_data["local_port"] = utils.get_random_open_local_port()
        data = copy.deepcopy(request_data)

        # Manual check for uniqueness
        prev_model = self.queryset.filter(backend_id=request.data["backend_id"]).first()
        if prev_model is not None:
            self.perform_destroy(prev_model, log.warning)

        # start tunnel
        try:
            if not utils.start_tunnel(**data):
                return Response(status=utils.COULD_NOT_START_TUNNEL)
        except utils.SystemNotAvailableException:
            return Response(status=utils.SYSTEM_NOT_AVAILABLE_STATUS)

        # super().create with different data
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @request_decorator
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {"running": True}
        if not utils.is_port_in_use(instance.local_port):
            data["running"] = False
        return Response(data)

    def perform_destroy(self, instance, log_func=None):
        kwargs = self.get_kwargs(instance)
        if log_func:
            log_func("Delete tunnel", extra=kwargs)
        try:
            utils.stop_tunnel(**kwargs)
        except:
            pass
        return super().perform_destroy(instance)

    @request_decorator
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance, log.info)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RemoteViewSet(viewsets.ModelViewSet):
    serializer_class = RemoteSerializer
    queryset = RemoteModel.objects.all()

    lookup_field = "hostname"

    permission_classes = [HasGroupPermission]
    required_groups = ["access_to_webservice"]

    def get_kwargs(self, instance=None, data=None):
        if instance:
            kwargs = {
                "hostname": instance.hostname,
                "running": instance.running,
                "updated_at": instance.updated_at,
            }
        elif data is None:
            if type(self.request.data) != dict:
                kwargs = {
                    "hostname": self.request.data["hostname"],
                }
            else:
                kwargs = copy.deepcopy(self.request.data)
        else:
            kwargs = copy.deepcopy(data)
        kwargs["uuidcode"] = self.request.query_params.get("uuidcode", "no-uuidcode")
        return kwargs

    @request_decorator
    def create(self, request, *args, **kwargs):
        try:
            running = utils.start_remote(**self.get_kwargs())
        except utils.SystemNotAvailableException:
            return Response(status=utils.SYSTEM_NOT_AVAILABLE_STATUS)
        hostname = request.data["hostname"]
        if type(hostname) == list:
            hostname = hostname[0]
        RemoteModel.objects.update_or_create(
            hostname=request.data["hostname"], defaults={"running": running}
        )
        return Response(data={"running": running}, status=status.HTTP_201_CREATED)

    @request_decorator
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            kwargs = self.get_kwargs(instance)
        except Http404 as e:
            kwargs = self.get_kwargs(data=kwargs)
        running = utils.status_remote(**kwargs)
        print(running)
        print("------")
        RemoteModel.objects.update_or_create(
            hostname=kwargs["hostname"], defaults={"running": running}
        )
        return Response({"running": running})

    @request_decorator
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            kwargs = self.get_kwargs(instance)
        except Http404 as e:
            kwargs = self.get_kwargs(data=kwargs)
        print(kwargs)
        utils.stop_remote(**kwargs)
        print("Update")
        RemoteModel.objects.update_or_create(
            hostname=kwargs["hostname"], defaults={"running": False}
        )
        print("Updated")
        return Response()
