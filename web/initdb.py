import os

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from logs.models import HandlerModel


def create_user(username, passwd, groups=[], superuser=False, mail=""):
    if User.objects.filter(username=username).exists():
        return
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


def setup_logger():
    data = {
        "handler": "stream",
        "configuration": {
            "level": 10,
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
    }
    HandlerModel(**data).save()


if __name__ == "__main__":
    user_groups = {
        "jupyterhub": ["access_to_webservice", "access_to_logging"],
        "k8smgr": ["access_to_webservice_restart"],
        "remotecheck": ["access_to_webservice_remote_check"],
    }

    superuser_name = "admin"
    superuser_mail = os.environ.get("SUPERUSER_MAIL", "admin@example.com")
    superuser_pass = os.environ["SUPERUSER_PASS"]
    create_user(superuser_name, superuser_pass, superuser=True, mail=superuser_mail)

    for username, groups in user_groups.items():
        userpass = os.environ.get(f"{username.upper()}_USER_PASS", None)
        if userpass:
            create_user(username, userpass, groups=groups)

    setup_logger()
