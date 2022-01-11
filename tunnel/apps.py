import logging

from django.apps import AppConfig
from django.db.utils import OperationalError

from jupyterjsc_tunneling.settings import LOGGER_NAME
from tunnel.utils import k8s_svc
from tunnel.utils import start_tunnel
from tunnel.utils import stop_tunnel

log = logging.getLogger(LOGGER_NAME)


class TunnelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tunnel"

    def start_tunnels_in_db(self):
        from .models import TunnelModel

        uuidcode = "StartUp"
        log.info("Start db-tunnels", extra={"uuidcode": uuidcode})

        kwargs = {"uuidcode": "uuidcode"}
        tunnels = TunnelModel.objects.all()
        for tunnel in tunnels:
            try:
                kwargs["backend_id"] = tunnel.backend_id
                kwargs["hostname"] = tunnel.hostname
                kwargs["local_port"] = tunnel.local_port
                kwargs["target_node"] = tunnel.target_node
                kwargs["target_port"] = tunnel.target_port
                start_tunnel(**kwargs)
            except:
                log.exception("Could not start ssh tunnel at StartUp", extra=kwargs)
                log.info("Delete k8s svc, if it exists")
                try:
                    k8s_svc("delete", alert_admins=True, **kwargs)
                except:
                    log.exception("Could not delete k8s service", extra=kwargs)
                continue
            try:
                log.info("Create k8s svc")
                k8s_svc("create", alert_admins=True, **kwargs)
            except:
                log.exception("Could not create k8s service", extra=kwargs)
                try:
                    stop_tunnel(**kwargs)
                except:
                    log.exception("Could not stop ssh tunnel", extra=kwargs)

    def ready(self):
        try:
            self.start_tunnels_in_db()
        except OperationalError:
            pass
        return super().ready()
