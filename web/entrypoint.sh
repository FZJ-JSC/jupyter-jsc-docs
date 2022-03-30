#!/bin/bash

USERNAME=${USERNAME}

# Start sshd service
export SSHD_LOG_PATH=${SSHD_LOG_PATH:-/home/${USERNAME}/sshd.log}
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

if [[ -d /tmp/${USERNAME}_ssh ]]; then
    mkdir -p /home/${USERNAME}/.ssh
    cp -rp /tmp/${USERNAME}_ssh/* /home/${USERNAME}/.ssh/.
    chmod -R 400 /home/${USERNAME}/.ssh/*
    chown -R ${USERNAME}:users /home/${USERNAME}/.ssh
fi


# Set secret key
export SECRET_KEY=${SECRET_KEY:-$(uuidgen)}

# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
else
    export SQL_DATABASE=${SQL_DATABASE:-/home/${USERNAME}/web/db.sqlite3}
    if [[ ! -f ${SQL_DATABASE} ]]; then
        export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
        su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
        su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"
        su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import User; adminpass=os.environ.get('SUPERUSER_PASS'); User.objects.create_superuser('admin', 'admin@example.com', adminpass)\" | python3 manage.py shell"
        su ${USERNAME} -c "echo \"import os; from django.contrib.auth.models import Group; Group.objects.create(name='access_to_webservice'); Group.objects.create(name='access_to_webservice_restart'); Group.objects.create(name='access_to_logging');\" | python3 manage.py shell"
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
    echo "$(date) ... done"
fi

if [[ -z $WORKER ]]; then
        echo "Use 1 worker (default)"
        WORKER=1
fi

if [ -z ${UWSGI_PATH} ]; then
    export UWSGI_SSL_CRT=${UWSGI_SSL_CRT:-/home/${USERNAME}/certs/${USERNAME}.crt}
    export UWSGI_SSL_KEY=${UWSGI_SSL_KEY:-/home/${USERNAME}/certs/${USERNAME}.key}
    if [[ -f ${UWSGI_SSL_CRT} && -f ${UWSGI_SSL_KEY} ]]; then
        UWSGI_PATH=/home/${USERNAME}/web/uwsgi_https.ini
        echo "Use ${UWSGI_PATH} as config file. Service will listen on port 8443."
        echo "Use these files for ssl: ${UWSGI_SSL_CRT}, ${UWSGI_SSL_KEY}"
    else
        UWSGI_PATH=/home/${USERNAME}/web/uwsgi_http.ini
        echo "Use ${UWSGI_PATH} as config file. Service will listen on port 8080."
    fi
fi

# Set Defaults for uwsgi and start
export UWSGI_OFFLOAD_THREADS=${UWSGI_OFFLOAD_THREADS:-1}
export UWSGI_PROCESSES=${UWSGI_PROCESSES:-4}
export UWSGI_THREADS=${UWSGI_THREADS:-1}
uwsgi --ini ${UWSGI_PATH}
