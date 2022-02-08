#!/bin/bash

# Start ssh daemon
if [ -z ${SSHD_LOG_PATH} ]; then
    SSHD_LOG_PATH=/home/tunnel/sshd.log
fi
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

if [[ -n ${SSH_RO_PATH} ]]; then
    for f in ${SSH_RO_PATH}/* ; do
        if [[ -f $f ]]; then
            cp -rp $f /home/tunnel/.ssh/.
        fi
    done
fi

chown -R tunnel:users /home/tunnel/.ssh/*
chmod -R 400 /home/tunnel/.ssh/*

# Check for secret key
if [[ -z $TUNNEL_SECRET_KEY ]]; then
    export TUNNEL_SECRET_KEY=$(uuidgen)
fi

# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
elif [[ -z ${SQL_DATABASE} ]]; then
    if [[ -z $TUNNEL_SUPERUSER_PASS ]]; then
        export TUNNEL_SUPERUSER_PASS=$(uuidgen)
    fi
    su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py makemigrations"
    su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py migrate"
    su tunnel -c "echo \"import os; from django.contrib.auth.models import User; tunnelpass=os.environ.get('TUNNEL_SUPERUSER_PASS'); User.objects.create_superuser('admin', 'admin@example.com', tunnelpass)\" | python manage.py shell"
    su tunnel -c "echo \"import os; from django.contrib.auth.models import Group; Group.objects.create(name='access_to_webservice'); Group.objects.create(name='access_to_logging');\" | python manage.py shell"
    if [[ -n ${BACKEND_USER_PASS} ]]; then
        su tunnel -c "echo \"import os; from django.contrib.auth.models import Group, User; from rest_framework.authtoken.models import Token; backend_pass=os.environ.get('BACKEND_USER_PASS'); user = User.objects.create(username='backend'); user.set_password(backend_pass); user.save(); user.auth_token = Token.objects.create(user=user); os.environ['BACKEND_USER_TOKEN'] = user.auth_token.key; group1 = Group.objects.filter(name='access_to_webservice').first(); group2 = Group.objects.filter(name='access_to_logging').first(); user.groups.add(group1); user.groups.add(group2)\" | python manage.py shell"
    fi
    if [[ -n ${JUPYTERHUB_USER_PASS} ]]; then
        su tunnel -c "echo \"import os; from django.contrib.auth.models import Group, User; from rest_framework.authtoken.models import Token; jhub_pass=os.environ.get('JUPYTERHUB_USER_PASS'); user = User.objects.create(username='jupyterhub'); user.set_password(jhub_pass); user.save(); user.auth_token = Token.objects.create(user=user); os.environ['JUPYTERHUB_USER_TOKEN'] = user.auth_token.key; group1 = Group.objects.filter(name='access_to_webservice').first(); group2 = Group.objects.filter(name='access_to_logging').first(); user.groups.add(group1); user.groups.add(group2)\" | python manage.py shell"
    fi
fi

if [[ ! -d /home/tunnel/web/static ]]; then
    echo "$(date) Collect static files ..."
    su tunnel -c "SQL_DATABASE=/dev/null /usr/local/bin/python3 /home/tunnel/web/manage.py collectstatic"
    echo "$(date) ... done"
fi

if [[ -z $WORKER ]]; then
        echo "Use 1 worker (default)"
        WORKER=1
fi

if [ -z ${UWSGI_PATH} ]; then
    UWSGI_PATH=/home/tunnel/web/uwsgi.ini
fi

if [[ -n ${DELAYED_START_IN_SEC} ]]; then
    echo "$(date): Delay start by ${DELAYED_START_IN_SEC} seconds ..."
    sleep ${DELAYED_START_IN_SEC}
    echo "$(date): ... done"
fi

if [[ ${DEVEL,,} == "true" ]]; then
    if [[ -d /tmp/.vscode ]]; then
        cp -r /tmp/.vscode /home/tunnel/.
    fi
    if [[ -d /tmp/home ]]; then
        cp -r /tmp/home/* /home/tunnel/.
    fi
    apt update && apt install rsync vim
    while true; do
        sleep 30
    done
else
    uwsgi --ini ${UWSGI_PATH} --processes ${WORKER}
fi
