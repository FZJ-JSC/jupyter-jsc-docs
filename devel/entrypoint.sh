#!/bin/bash

USERNAME=tunnel

# Start sshd service
if [[ -n $AUTHORIZED_KEYS_PATH ]]; then
    sed -i -e "s@.ssh/authorized_keys@${AUTHORIZED_KEYS_PATH}@g" /etc/ssh/sshd_config
fi
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
fi
export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"
echo "$(date) Admin password: ${SUPERUSER_PASS}"

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
