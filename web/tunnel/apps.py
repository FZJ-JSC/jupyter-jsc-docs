import copy
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
from forwarder.utils.k8s import get_tunnel_sts_pod_names


log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class TunnelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tunnel"

    def start_tunnels_in_db(self):
        from .models import TunnelModel

        podname = os.environ.get("HOSTNAME", "drf-tunnel-0")
        uuidcode = "StartUp Tunnel"
        log.info("Start all tunnels saved in database", extra={"uuidcode": uuidcode, "pod": podname})
        tunnels = TunnelModel.objects.filter(tunnel_pod=podname).all()
        for tunnel in tunnels:
            try:
                kwargs = {}
                for key, value in tunnel.__dict__.items():
                    if key not in ["date", "_state"]:
                        kwargs[key] = copy.deepcopy(value)
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
            log.debug("Create k8s svc")
            k8s_svc("create", alert_admins=True, raise_exception=False, **kwargs)

    def create_user(self, username, passwd, groups=[], superuser=False, mail=""):
        from django.contrib.auth.models import Group
        from django.contrib.auth.models import User

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

    def setup_db(self):
        user_groups = {}
        for key in os.environ.keys():
            if key.endswith("_USER_PASS"):
                username = key[: -len("_USER_PASS")].lower()
                if username == "jupyterhub":
                    user_groups[username] = [
                        "access_to_webservice",
                        "access_to_logging",
                    ]
                elif username.startswith("k8smgr"):
                    user_groups[username] = ["access_to_webservice_restart"]
                elif username.startswith("remotecheck"):
                    user_groups[username] = ["access_to_webservice_remote_check"]
                elif username.startswith("tunnel"):
                    user_groups[username] = [
                        "access_to_webservice",
                        "access_to_webservice_restart",
                    ]
                else:
                    user_groups[username] = ["access_to_webservice"]

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
            else:
                log.info(
                    f"Do not create user {username} - password is missing",
                    extra={"uuidcode": "StartUp"},
                )

    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_logger()
            self.setup_db()
            try:
                self.start_tunnels_in_db()
            except:
                log.exception("Unexpected error during startup", extra={"uuidcode": "StartUp"})
            try:
                podname = os.environ.get("HOSTNAME", "drf-tunnel-0")
                log.info("Get tunnel sts pod name", extra={"uuidcode": "StartUp"})
                tunnel_pods = get_tunnel_sts_pod_names()
                log.info(f"Get tunnel sts pod name: {tunnel_pods}", extra={"uuidcode": "StartUp"})
                # Only start remote tunnels on first pod of stateful set
                if podname == tunnel_pods[0]:
                    log.info("Start remote tunnels from config file on drf-tunnel-0", extra={"uuidcode": "StartUp"})
                    start_remote_from_config_file(uuidcode="StartUp")
                    log.info("Start remote tunnels from config file on drf-tunnel-0 finished", extra={"uuidcode": "StartUp"})
            except:
                log.exception("Unexpected error during startup", extra={"uuidcode": "StartUp"})
        log.info("Ready function finished. Start webservice.", extra={"uuidcode": "StartUp"})
        return super().ready()
