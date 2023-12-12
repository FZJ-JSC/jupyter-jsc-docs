import copy
import logging
import multiprocessing
import os

import yaml

# We might want to log forbidden extra keywords like "filename".
# Instead of raising an exception, we just alter the keyword
class ExtraLoggerClass(logging.Logger):
    def trace(self, message, *args, **kws):
        if self.isEnabledFor(5):
            # Yes, logger takes its '*args' as 'args'.
            self._log(5, message, args, **kws)

    def makeRecord(
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        """
        A factory method which can be overridden in subclasses to create
        specialized LogRecords.
        """
        rv = logging._logRecordFactory(
            name, level, fn, lno, msg, args, exc_info, func, sinfo
        )
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    rv.__dict__[f"{key}_extra"] = extra[key]
                else:
                    rv.__dict__[key] = extra[key]
        return rv


logging.setLoggerClass(ExtraLoggerClass)

from django.apps import AppConfig
from jupyterjsc_tunneling.settings import LOGGER_NAME
from jupyterjsc_tunneling.logs import update_extra_handlers
from tunnel.utils import k8s_svc
from tunnel.utils import start_remote
from tunnel.utils import start_remote_from_config_file
from tunnel.utils import start_tunnel
from tunnel.utils import stop_and_delete
from tunnel.utils import stop_tunnel
from forwarder.utils.k8s import get_tunnel_sts_pod_names

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"

background_tasks = []

# For all workers: init logging
_logging_config_cache = {}
_logging_config_last_update = 0
_logging_config_file = os.environ.get("LOGGING_CONFIG_PATH")

try:
    with open(_logging_config_file, "r") as f:
        conf = yaml.full_load(f)
    update_extra_handlers(conf)
except:
    print("Could not initial logging file")


class TunnelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tunnel"

    def start_tunnels_in_db(self):
        from .models import TunnelModel

        podname = os.environ.get("HOSTNAME", "drf-tunnel-0")
        uuidcode = "StartUp Tunnel"
        log.info(
            "Start all tunnels saved in database",
            extra={"uuidcode": uuidcode, "pod": podname},
        )
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

    def setup_db(self):
        superuser_name = "admin"
        superuser_mail = os.environ.get("SUPERUSER_MAIL", "admin@example.com")
        superuser_pass = os.environ["SUPERUSER_PASS"]
        self.create_user(
            superuser_name, superuser_pass, superuser=True, mail=superuser_mail
        )
        _users = {}
        usernames_via_env = [x for x in os.environ.get("usernames", "").split(";") if x]
        passwords_via_env = [x for x in os.environ.get("passwords", "").split(";") if x]
        groups_via_env = [
            [y for y in x.split(":") if y]
            for x in os.environ.get("groups", "").split(";")
        ]
        if usernames_via_env and passwords_via_env:
            for i in range(len(usernames_via_env)):
                if i >= len(passwords_via_env):
                    log.warning(
                        f"No password available for {usernames_via_env[i]}. User not created."
                    )
                else:
                    groups = []
                    try:
                        groups = groups_via_env[i]
                    except:
                        log.warning(
                            f"No groups available for {usernames_via_env[i]}. Use default groups [access_to_webservice]"
                        )
                        groups = ["access_to_webservice"]
                    self.create_user(
                        usernames_via_env[i], passwords_via_env[i], groups=groups
                    )

    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_db()
            try:
                self.start_tunnels_in_db()
            except:
                log.exception(
                    "Unexpected error during startup", extra={"uuidcode": "StartUp"}
                )
            try:
                podname = os.environ.get("HOSTNAME", "drf-tunnel-0")
                log.info("Get tunnel sts pod name", extra={"uuidcode": "StartUp"})
                tunnel_pods = get_tunnel_sts_pod_names()
                log.info(
                    f"Get tunnel sts pod name: {tunnel_pods}",
                    extra={"uuidcode": "StartUp"},
                )
                # Only start remote tunnels on first pod of stateful set
                if podname == tunnel_pods[0]:
                    global background_tasks
                    log.info(
                        "Start remote tunnels from config file on drf-tunnel-0",
                        extra={"uuidcode": "StartUp"},
                    )
                    proc = multiprocessing.Process(
                        target=start_remote_from_config_file,
                        args=("PeriodicCheck", "", True),
                    )
                    background_tasks.append(proc)
                    proc.start()
                    log.info(
                        "Start remote tunnels from config file on drf-tunnel-0 finished",
                        extra={"uuidcode": "StartUp"},
                    )
            except:
                log.exception(
                    "Unexpected error during startup", extra={"uuidcode": "StartUp"}
                )
        log.info(
            "Ready function finished. Start webservice.", extra={"uuidcode": "StartUp"}
        )
        return super().ready()
