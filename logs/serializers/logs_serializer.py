from rest_framework import serializers

from ..models.logs_models import HandlerModel


class HandlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlerModel
        fields = ["handler", "configuration"]
