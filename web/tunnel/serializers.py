import copy
import json
import os
import re
from typing import Dict

from django.http import QueryDict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer

from .models import TunnelModel
from .utils import get_custom_headers
from .utils import get_random_open_local_port
from .utils import is_port_in_use
from .utils import status_remote
from .utils import stop_and_delete


class TunnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelModel
        fields = [
            "servername",
            "hostname",
            "svc_name",
            "local_port",
            "svc_port",
            "target_node",
            "target_port",
            "tunnel_pod",
            "jhub_userid",
            "jhub_credential",
        ]

    def check_input_keys(self, required_keys):
        for key in required_keys:
            if key not in self.initial_data.keys():
                self._validated_data = []
                self._errors = [f"Missing key in input data: {key}"]
                raise ValidationError(self._errors)
        custom_headers = get_custom_headers(self.context["request"]._request.META)
        if "labels" in custom_headers:
            try:
                labels = json.loads(custom_headers["labels"])
                if not isinstance(labels, dict):
                    raise
            except:
                self._validated_data = []
                self._errors = [f"Key labels must be a dict, got {type(labels)}"]
                raise ValidationError(self._errors)
            r = r"^[A-Za-z0-9][A-Za-z0-9._\-]*$"
            for value in labels.values():
                if not re.search(r, value):
                    self._validated_data = []
                    self._errors = [
                        f"Label values must start with an alphanumerical and can only contain the special characters `.`, `-`, and `_`, got {value}"
                    ]
                    raise ValidationError(self._errors)

    def is_valid(self, raise_exception=False):
        required_keys = [
            "servername",
            "hostname",
            "svc_name",
            "svc_port",
            "target_node",
            "target_port",
            "jhub_userid",
        ]
        try:
            self.check_input_keys(required_keys)
        except ValidationError as exc:
            _errors = exc.detail
        else:
            _errors = {}
        if _errors and raise_exception:
            raise ValidationError(_errors)

        servername = self.initial_data["servername"]
        prev_model = TunnelModel.objects.filter(servername=servername).first()
        if prev_model is not None:
            kwargs = {}
            for key, value in prev_model.__dict__.items():
                if key not in ["date", "_state"]:
                    kwargs[key] = copy.deepcopy(value)
            kwargs["uuidcode"] = servername
            stop_and_delete(**kwargs)
            prev_model.delete()
        return super().is_valid(raise_exception=raise_exception)

    def to_internal_value(self, data):
        jhub_credential = self.context["request"].user.username
        data["local_port"] = get_random_open_local_port()
        data.pop("labels", None)
        data["tunnel_pod"] = os.environ.get("HOSTNAME", "drf-tunnel-0")
        data["jhub_credential"] = jhub_credential
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["running"] = is_port_in_use(instance.local_port)
        return ret


class TunnelUpdateSerializer(TunnelSerializer):
    def to_internal_value(self, data):
        data = data.dict()
        data["local_port"] = int(data["local_port"])
        return data

    def is_valid(self, raise_exception=False):
        required_keys = [
            "servername",
            "hostname",
            "svc_name",
            "svc_port",
            "target_node",
            "target_port",
            "jhub_userid",
        ]
        try:
            self.check_input_keys(required_keys)
        except ValidationError as exc:
            _errors = exc.detail
        else:
            _errors = {}
        if _errors and raise_exception:
            raise ValidationError(_errors)
        return super(TunnelSerializer, self).is_valid(raise_exception=raise_exception)


class RemoteSerializer(Serializer):
    _errors = {}

    def is_valid(self, raise_exception=False):
        # _errors = {}
        required_keys = ["hostname"]
        for key in required_keys:
            if key not in self.initial_data.keys():
                self._validated_data = []
                self._errors = [f"Missing key in input data: {key}"]
        if self._errors and raise_exception:
            raise ValidationError(self._errors)
        return super().is_valid(raise_exception=raise_exception)

    def to_internal_value(self, data):
        data["running"] = status_remote(alert_admins=True, raise_exception=True, **data)
        return data
