import copy

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import HandlerModel
from .utils import default_configurations


class HandlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlerModel
        fields = ["handler", "configuration"]

    def is_valid_config(self, name, valid_values, handler=None, case_sensitive=True):
        value = self.initial_data.get("configuration", {}).get(name, None)
        if value and not case_sensitive:
            value = value.lower()
        if handler is None or handler == self.initial_data["handler"]:
            if value is not None and value not in valid_values:
                self._errors = [
                    f"Unsupported {name}: {value}. Supported {name}s: {valid_values}"
                ]
                raise ValidationError(self._errors)

    def is_valid_config_type(self, name, valid_value_types, handler=None):
        if type(valid_value_types) != list:
            valid_value_types = [valid_value_types]
        value = self.initial_data.get("configuration", {}).get(name, None)
        if handler is None or handler == self.initial_data["handler"]:
            if value is not None and type(value) not in valid_value_types:
                self._errors = [
                    f"{name} in configuration must be of type {valid_value_types} not {type(value)}"
                ]
                raise ValidationError(self._errors)

    def is_valid(self, raise_exception=False):
        try:
            allowed_handlers = ["stream", "file", "smtp", "syslog"]
            if "handler" not in self.initial_data.keys():
                raise ValidationError(["Missing key in input data: handler"])
            handler = self.initial_data["handler"]
            if handler not in allowed_handlers:
                self._errors = [
                    f"Unsupported handler: {handler}. Supported handlers: {allowed_handlers}"
                ]
                raise ValidationError(self._errors)
            if "configuration" in self.initial_data.keys():
                configuration_type = type(self.initial_data["configuration"])
                if configuration_type != dict:
                    self._errors = [
                        f"Configuration must be of type dict not {configuration_type}"
                    ]
                    raise ValidationError(self._errors)
                self.is_valid_config("formatter", ["simple", "json"])
                valid_levels = [
                    0,
                    5,
                    10,
                    20,
                    30,
                    40,
                    50,
                    99,
                    "0",
                    "5",
                    "10",
                    "20",
                    "30",
                    "40",
                    "50",
                    "99",
                    "NOTSET",
                    "TRACE",
                    "DEBUG",
                    "INFO",
                    "WARN",
                    "WARNING",
                    "ERROR",
                    "FATAL",
                    "CRITICAL",
                    "DEACTIVATE",
                ]
                self.is_valid_config("level", valid_levels)
                self.is_valid_config(
                    "stream", ["ext://sys.stdout", "ext://sys.stderr"], "stream"
                )
                self.is_valid_config_type("filename", [str], "file")
                self.is_valid_config(
                    "when",
                    [
                        "s",
                        "m",
                        "h",
                        "d",
                        "w0",
                        "w1",
                        "w2",
                        "w3",
                        "w4",
                        "w5",
                        "w6",
                        "midnight",
                    ],
                    "file",
                    False,
                )
                self.is_valid_config_type("backupCount", [int], "file")
                self.is_valid_config_type("mailhost", [str], "smtp")
                self.is_valid_config_type("fromaddr", [str], "smtp")
                self.is_valid_config_type("toaddrs", [list], "smtp")
                self.is_valid_config_type("subject", [str], "smtp")
                self.is_valid_config_type("address", [list], "syslog")
                self.is_valid_config(
                    "socktype",
                    ["ext://socket.SOCK_STREAM", "ext://socket.SOCK_DGRAM"],
                    "syslog",
                )
        except ValidationError as exc:
            self._validated_data = {}
        else:
            self._errors = {}

        if self._errors and raise_exception:
            raise ValidationError(self._errors)

        return super().is_valid(raise_exception)

    def to_internal_value(self, data):
        handler_name = data["handler"]
        existing_handler = HandlerModel.objects.filter(handler=handler_name).first()
        if existing_handler is not None:
            configuration = copy.deepcopy(existing_handler.configuration)
        else:
            configuration = copy.deepcopy(default_configurations[handler_name])
        for key, value in data.get("configuration", {}).items():
            configuration[key] = value
        data["configuration"] = configuration
        return super().to_internal_value(data)
