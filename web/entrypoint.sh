#!/bin/bash

USERNAME=${USERNAME}

# Start sshd service
if [[ -n $AUTHORIZED_KEYS_PATH ]]; then
    sed -i -e "s@.ssh/authorized_keys@${AUTHORIZED_KEYS_PATH}@g" /etc/ssh/sshd_config
fi
export SSHD_LOG_PATH=${SSHD_LOG_PATH:-/home/${USERNAME}/sshd.log}
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

# Set secret key
export SECRET_KEY=${SECRET_KEY:-$(uuidgen)}

# Database setup / wait for database
export SQL_DATABASE=${SQL_DATABASE:-/home/${USERNAME}/web/db.sqlite3}
if [ "$SQL_ENGINE" == "django.db.backends.postgresql" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi
export SUPERUSER_PASS=${SUPERUSER_PASS:-$(uuidgen)}
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py makemigrations"
su ${USERNAME} -c "python3 /home/${USERNAME}/web/manage.py migrate"

if [[ -n ${TUNNEL_USER_PASS} ]]; then
  export TUNNEL_USERNAME=${TUNNEL_USERNAME:-tunnel}
  export TUNNEL_AUTHENTICATION_TOKEN=${TUNNEL_AUTHENTICATION_TOKEN:-"Basic $(echo -n "${TUNNEL_USERNAME}:${TUNNEL_USER_PASS}" | base64 -w 0)"}
fi

if [[ ! -d /home/${USERNAME}/web/static ]]; then
    echo "$(date) Collect static files ..."
    su ${USERNAME} -c "SQL_DATABASE=/dev/null python3 /home/${USERNAME}/web/manage.py collectstatic"
    echo "$(date) ... done"
fi

if [ -z ${GUNICORN_PATH} ]; then
    export GUNICORN_SSL_CRT=${GUNICORN_SSL_CRT:-/home/${USERNAME}/certs/${USERNAME}.crt}
    export GUNICORN_SSL_KEY=${GUNICORN_SSL_KEY:-/home/${USERNAME}/certs/${USERNAME}.key}
    if [[ -f ${GUNICORN_SSL_CRT} && -f ${GUNICORN_SSL_KEY} ]]; then
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_https.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8443."
        echo "Use these files for ssl: ${GUNICORN_SSL_CRT}, ${GUNICORN_SSL_KEY}"
    else
        GUNICORN_PATH=/home/${USERNAME}/web/gunicorn_http.py
        echo "Use ${GUNICORN_PATH} as config file. Service will listen on port 8080."
    fi
fi

# Set Defaults for gunicorn and start
export GUNICORN_PROCESSES=${GUNICORN_PROCESSES:-16}
export GUNICORN_THREADS=${GUNICORN_THREADS:-1}
gunicorn -c ${GUNICORN_PATH} jupyterjsc_tunneling.wsgi
