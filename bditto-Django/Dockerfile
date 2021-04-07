#FROM python:alpine3.7
FROM python:3.7.2
#FROM python:3.8-alpine
RUN apt-get update
RUN apt-get install gcc
#RUN apk update && \
#    apk add --virtual build-deps gcc python-dev musl-dev

RUN mkdir -p /app
WORKDIR /app
RUN pip install --upgrade pip
RUN python -m venv venv
RUN . venv/bin/activate
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
RUN pip install channels --upgrade
ENV DJANGO_SETTINGS_MODULE=samePinch.settings.local
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_PASSWORD=admin123
ENV DJANGO_SUPERUSER_EMAIL=rhlbatra7@gmail.com
#WORKDIR /app
EXPOSE 8003
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
#CMD ["/start.sh"]
CMD  ["sh", "start.sh", "run"]

