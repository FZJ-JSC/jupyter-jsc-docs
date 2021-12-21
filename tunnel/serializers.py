from rest_framework import serializers

from .models import TunnelModel


class TunnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TunnelModel
        fields = ["backend_id", "hostname", "local_port", "target_node", "target_port"]

    def is_valid(self, raise_exception=False):
        return super().is_valid(raise_exception=raise_exception)
