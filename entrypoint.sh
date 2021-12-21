#!/bin/sh

lsof -v &> /dev/null
LSOF_EC=$?

if [[ ! $LSOF_EC -eq 0 ]]; then
    echo "lsof is not installed"
    exit 255
fi

/usr/sbin/sshd -f /etc/ssh/sshd_config -E /mnt/config/logs/sshd.log

if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi

if [[ -n ${1} ]]; then
        echo "Use Arguments: ${@}"
        WORKER=${1}
fi
if [[ -z $WORKER ]]; then
        echo "Use 1"
        WORKER=1
fi

# Requirement for psycopg2, even if it's not marked by psycopg2 as requirement
export LD_PRELOAD=/lib/libssl.so.1.1

if [[ "$SQL_MIGRATE" -eq "1" ]]; then
        su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py makemigrations"
        su tunnel -c "/usr/local/bin/python3 /home/tunnel/web/manage.py migrate"
fi

/usr/local/bin/python3 /home/tunnel/web/logging_receiver.py &

su tunnel -c "uwsgi --ini /mnt/config/uwsgi.ini --processes ${WORKER}"
