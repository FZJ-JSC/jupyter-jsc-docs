import json

from django.db import models


class HandlerModel(models.Model):
    handler = models.TextField("handler", primary_key=True)
    configuration = models.JSONField("configuration", null=False)

    def __str__(self):
        return f"{self.handler} - {json.dumps(self.configuration, sort_keys=True, indent=2)}"
