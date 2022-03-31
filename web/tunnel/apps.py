import logging
import os

from django.apps import AppConfig
from jupyterjsc_tunneling.settings import LOGGER_NAME
from tunnel.utils import k8s_svc
from tunnel.utils import start_remote
from tunnel.utils import start_remote_from_config_file
from tunnel.utils import start_tunnel
from tunnel.utils import stop_and_delete
from tunnel.utils import stop_tunnel


log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class TunnelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tunnel"

    def start_tunnels_in_db(self):
        from .models import TunnelModel

        uuidcode = "StartUp Tunnel"
        log.info("Start all tunnels saved in database", extra={"uuidcode": uuidcode})
        tunnels = TunnelModel.objects.all()
        for tunnel in tunnels:
            try:
                kwargs = tunnel.__dict__
                kwargs["uuidcode"] = uuidcode
                start_tunnel(**kwargs)
            except:
                log.exception("Could not start ssh tunnel at StartUp", extra=kwargs)
                log.debug("Delete k8s svc, if it exists", extra=kwargs)
                try:
                    k8s_svc("delete", alert_admins=True, **kwargs)
                except:
                    log.debug(
                        "Could not delete k8s service", extra=kwargs, exc_info=True
                    )
                continue
            try:
                log.debug("Create k8s svc")
                k8s_svc("create", alert_admins=True, **kwargs)
            except:
                log.warning(
                    "Could not create k8s service. Stop/Delete tunnel",
                    extra=kwargs,
                    exc_info=True,
                )
                try:
                    stop_and_delete(raise_exception=False, **kwargs)
                    tunnel.delete()
                except:
                    log.exception("Could not stop/delete ssh tunnel", extra=kwargs)

    def ready(self):
        if os.environ.get("UWSGI_START", "false").lower() == "true":
            try:
                self.start_tunnels_in_db()
            except:
                log.exception("Unexpected error during startup")
            try:
                start_remote_from_config_file(uuidcode="StartUp")
            except:
                log.exception("Unexpected error during startup")
        return super().ready()
