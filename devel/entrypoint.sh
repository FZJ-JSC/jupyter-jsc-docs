#!/bin/bash

USERNAME=tunnel

# Start sshd service
export SSHD_LOG_PATH=${SSHD_LOG_PATH:-/home/${USERNAME}/sshd.log}
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

if [[ -d /tmp/${USERNAME}_ssh ]]; then
    mkdir -p /home/${USERNAME}/.ssh
    cp -rp /tmp/${USERNAME}_ssh/* /home/${USERNAME}/.ssh/.
    chmod -R 400 /home/${USERNAME}/.ssh/*
fi

# Set secret key
export SECRET_KEY=${SECRET_KEY:-$(uuidgen)}

# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
        sleep 0.1
    done
    echo "$(date) PostgreSQL started"
else
    export SQL_DATABASE=${SQL_DATABASE:-/home/${USERNAME}/web/db.sqlite3}
    if [[ ! -f ${SQL_DATABASE} ]]; then
        export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
        su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
        su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"
        su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import User; adminpass=os.environ.get('SUPERUSER_PASS'); User.objects.create_superuser('admin', 'admin@example.com', adminpass)\" | python3 manage.py shell"
        su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import Group; Group.objects.create(name='access_to_webservice'); Group.objects.create(name='access_to_logging');\" | python3 manage.py shell"
        su ${USERNAME} -c "echo \"from logs.models import HandlerModel; data = {'handler': 'stream', 'configuration': {'level': 10, 'formatter': 'simple', 'stream': 'ext://sys.stdout'}}; HandlerModel(**data).save()\" | python3 manage.py shell"
        echo "$(date) Admin password: ${SUPERUSER_PASS}"
        if [[ -n ${JUPYTERHUB_USER_PASS} ]]; then
            su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import Group, User; from rest_framework.authtoken.models import Token; jhub_pass=os.environ.get('JUPYTERHUB_USER_PASS'); user = User.objects.create(username='jupyterhub'); user.set_password(jhub_pass); user.save(); user.auth_token = Token.objects.create(user=user); os.environ['JUPYTERHUB_USER_TOKEN'] = user.auth_token.key; group1 = Group.objects.filter(name='access_to_webservice').first(); group2 = Group.objects.filter(name='access_to_logging').first(); user.groups.add(group1); user.groups.add(group2)\" | python3 manage.py shell"
        fi
        if [[ -n ${K8SMGR_USER_PASS} ]]; then
            su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import Group, User; from rest_framework.authtoken.models import Token; k8smgr_pass=os.environ.get('K8SMGR_USER_PASS'); user = User.objects.create(username='k8smgr'); user.set_password(k8smgr_pass); user.save(); user.auth_token = Token.objects.create(user=user); os.environ['K8SMGR_USER_TOKEN'] = user.auth_token.key; group1 = Group.objects.filter(name='access_to_webservice_restart').first(); user.groups.add(group1)\" | python3 manage.py shell"
        fi
    fi
fi

if [[ ! -d /home/${USERNAME}/web/static ]]; then
    echo "$(date) Collect static files ..."
    su ${USERNAME} -c "SQL_DATABASE=/dev/null python3 /home/${USERNAME}/web/manage.py collectstatic"
    echo "$(date) Collect static files ... done"
fi

export GUNICORN_SSL_CRT=${GUNICORN_SSL_CRT:-/home/${USERNAME}/certs/${USERNAME}.crt}
export GUNICORN_SSL_KEY=${GUNICORN_SSL_KEY:-/home/${USERNAME}/certs/${USERNAME}.key}
export GUNICORN_PROCESSES=${GUNICORN_PROCESSES:-16}
export GUNICORN_THREADS=${GUNICORN_THREADS:-1}

if [[ -d /tmp/${USERNAME}_vscode ]]; then
    mkdir -p /home/${USERNAME}/web/.vscode
    cp -rp /tmp/${USERNAME}_vscode/* /home/${USERNAME}/web/.vscode/.
    find /home/${USERNAME}/web/.vscode -type f -exec sed -i '' -e "s@<KUBERNETES_SERVICE_HOST>@${KUBERNETES_SERVICE_HOST}@g" -e "s@<KUBERNETES_SERVICE_PORT>@${KUBERNETES_SERVICE_PORT}@g" {} \; 2> /dev/null
fi
if [[ -d /tmp/${USERNAME}_home ]]; then
    cp -rp /tmp/${USERNAME}_home/* /home/${USERNAME}/.
fi

chown -R ${USERNAME}:users /home/${USERNAME}

while true; do
    sleep 30
done
