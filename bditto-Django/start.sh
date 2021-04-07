#!/usr/bin/env bash
# start-server.sh
python manage.py migrate
python manage.py makemigrations
#python manage.py collectstatic
python manage.py makeadminuser --email rhlbatra7@gmail.com --username admin --password bditto1234
echo "username is $DJANGO_SUPERUSER_USERNAME"
#if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
#    (python manage.py createsuperuser --no-input)
#fi
#DJANGO_SUPERUSER_PASSWORD=testpass python manage.py createsuperuser --noinput --email=rhlbatra7@gmail.com --username=admin
#python manage.py runserver 0.0.0.0:8000
#ExecStart=/usr/local//bin/python /usr/local/bin/daphne -e ssl:8001:privateKey=/etc/letsencrypt/live/api.bditto.com/privkey.pem:certKey=/etc/letsencrypt/live/api.bditto.com/fullchain.pem
#ExecStart=/home/bditto/Bditto/benv/bin/python /home/bditto/Bditto/benv/bin/daphne -e ssl:8001:privateKey=/etc/letsencrypt/live/api.bditto.com/privkey.pem:certKey=/etc/letsencrypt/live/api.bditto.com/fullchain.pem samePinch.asgi:application
#ExecStart=/home/bditto/Bditto/benv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/run/gunicorn.sock samePinch.wsgi:application

#CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "mysite.wsgi:application"]
#gunicorn --bind 8003 --workers 3 samePinch.wsgi:application
gunicorn --bind 0.0.0.0:8003 samePinch.wsgi:application

