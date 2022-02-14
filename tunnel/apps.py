import logging
import os

from django.apps import AppConfig
from django.db.utils import OperationalError

from jupyterjsc_tunneling.settings import LOGGER_NAME
from tunnel.utils import k8s_svc
from tunnel.utils import start_remote
from tunnel.utils import start_tunnel
from tunnel.utils import stop_tunnel

log = logging.getLogger(LOGGER_NAME)


class TunnelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tunnel"

    def start_tunnels_in_db(self):
        from .models import TunnelModel

        uuidcode = "StartUp Tunnel"
        log.info("Start db-tunnels", extra={"uuidcode": uuidcode})
        tunnels = TunnelModel.objects.all()
        for tunnel in tunnels:
            try:
                kwargs = tunnel.__dict__
                kwargs["uuidcode"] = uuidcode
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

    def start_remote_in_config_file(self):
        kwargs = {"uuidcode": "StartUp"}
        config_file_path = os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config")
        try:
            with open(config_file_path, "r") as f:
                config_file = f.read().split("\n")
        except:
            log.critical(
                "Could not load ssh config file during startup",
                exc_info=True,
                extra=kwargs,
            )
            return
        remote_prefix = "Host remote_"
        remote_hosts_lines = [
            x[len(remote_prefix)] for x in config_file if x.startswith(remote_prefix)
        ]
        kwargs["remote_hosts"] = remote_hosts_lines
        log.info("Start db-remote-tunnels", extra=kwargs)
        for hostname in remote_hosts_lines:
            kwargs["hostname"] = hostname
            try:
                start_remote(**kwargs)
            except:
                log.exception(
                    "Could not start ssh remote tunnel at StartUp", extra=kwargs
                )

    def ready(self):
        if os.environ.get("UWSGI_START", "false").lower() == "true":
            try:
                self.start_tunnels_in_db()
            except OperationalError:
                pass

            try:
                self.start_remote_in_config_file()
            except OperationalError:
                pass
        return super().ready()
