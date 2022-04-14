import logging
import os

from django.apps import AppConfig
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
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

    def create_user(self, username, passwd, groups=[], superuser=False, mail=""):
        if User.objects.filter(username=username).exists():
            return
        log.info(f"Create user {username}", extra={"uuidcode": "StartUp"})
        if superuser:
            User.objects.create_superuser(username, mail, passwd)
            return
        else:
            user = User.objects.create(username=username)
            user.set_password(passwd)
            user.save()
        for group in groups:
            if not Group.objects.filter(name=group).exists():
                Group.objects.create(name=group)
            _group = Group.objects.filter(name=group).first()
            user.groups.add(_group)

    def setup_logger(self):
        from logs.models import HandlerModel

        data = {
            "handler": "stream",
            "configuration": {
                "level": 10,
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
        }
        HandlerModel(**data).save()

    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_logger()
            user_groups = {
                "jupyterhub": ["access_to_webservice", "access_to_logging"],
                "k8smgr": ["access_to_webservice_restart"],
                "remotecheck": ["access_to_webservice_remote_check"],
            }

            superuser_name = "admin"
            superuser_mail = os.environ.get("SUPERUSER_MAIL", "admin@example.com")
            superuser_pass = os.environ["SUPERUSER_PASS"]
            self.create_user(
                superuser_name, superuser_pass, superuser=True, mail=superuser_mail
            )

            for username, groups in user_groups.items():
                userpass = os.environ.get(f"{username.upper()}_USER_PASS", None)
                if userpass:
                    self.create_user(username, userpass, groups=groups)

            try:
                self.start_tunnels_in_db()
            except:
                log.exception("Unexpected error during startup")
            try:
                start_remote_from_config_file(uuidcode="StartUp")
            except:
                log.exception("Unexpected error during startup")
        return super().ready()
