from rest_framework import serializers

from .models import HandlerModel


class HandlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandlerModel
        fields = ["handler", "configuration"]
