from django.db import models


class TunnelModel(models.Model):
    startuuidcode = models.TextField(primary_key=True)
    hostname = models.TextField(null=False, max_length=32)
    local_port = models.IntegerField(null=False)
    target_node = models.TextField(null=False, max_length=32)
    target_port = models.IntegerField(null=False)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.startuuidcode}: ssh [...]@{self.hostname} -L {self.local_port}:{self.target_node}:{self.target_port}"
