#!/bin/sh

cd ${APP_HOME}
if [[ -n ${1} ]]; then
	echo "Use Arguments: ${@}"
	WORKER=${1}
fi
if [[ -z $WORKER ]]; then
	echo "Use 1"
	WORKER=1
fi

/usr/local/bin/python3 /home/tunnel/web/manage.py makemigrations
/usr/local/bin/python3 /home/tunnel/web/manage.py migrate
/usr/local/bin/python3 /home/tunnel/web/manage.py collectstatic

# set -a; source /mnt/config/local_container/.envs ; set +a

echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pass')" | python manage.py shell

uwsgi --ini /home/tunnel/web/uwsgi.ini.test --processes ${WORKER}
