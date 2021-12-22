#!/bin/sh

# Start ssh daemon
if [ -z ${SSHD_LOG_PATH} ]; then
    SSHD_LOG_PATH=/home/tunnel/sshd.log
fi
/usr/sbin/sshd -f /etc/ssh/sshd_config -E ${SSHD_LOG_PATH}

# Database setup / wait for database
if [ "$SQL_ENGINE" == "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
elif [[ -z ${SQL_DATABASE} ]]
    
    su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py makemigrations"
    su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py migrate"
    su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py collectstatic"
    su tunnel -c "export TUNNELPASS=$(uuidgen) echo \"import os; from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', os.environ['TUNNELPASS'])\" | python manage.py shell ; echo \"Admin password: $TUNNELPASS\""
fi

if [[ -z $WORKER ]]; then
        echo "Use 1 worker (default)"
        WORKER=1
fi

# Requirement for psycopg2, even if it's not marked by psycopg2 as requirement
# export LD_PRELOAD=/lib/libssl.so.1.1

if [ -z ${UWSGI_PATH} ]; then
    UWSGI_PATH=/home/tunnel/web/uwsgi.ini
fi

su tunnel -c "uwsgi --ini ${UWSGI_PATH} --processes ${WORKER}"
