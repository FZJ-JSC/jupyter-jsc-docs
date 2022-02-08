# pull official base image
# FROM alpine
FROM python:3.10.1-alpine3.15

RUN apk update && apk upgrade && apk add bash mailcap

# create directory for the app user
RUN mkdir -p /home/tunnel/ssh_socket && mkdir -p /home/tunnel/.ssh

# create the app user
RUN adduser --uid 1000 -D --gecos "" -G users tunnel

# create the appropriate directories
ENV HOME=/home/tunnel
ENV APP_HOME=/home/tunnel/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN apk update &&\
    apk add --no-cache bash openssh rssh libpq util-linux uwsgi uwsgi-python3 uwsgi-logfile &&\
    sed -i -r \
    -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" \
    -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" \
    -e "s/^#Port 22/Port 2222/g" \ 
    -e "s/^GatewayPorts no/GatewayPorts yes/g" \ 
    /etc/ssh/sshd_config && \
    ssh-keygen -A && \
    sed -i -e "s/^tunnel\:\!/tunnel:\*/g" /etc/shadow

RUN echo tunnel:$(uuidgen) | chpasswd

# copy project
COPY . $APP_HOME

RUN apk update && \
    apk add --no-cache --virtual .build-dependencies \
        gcc \
        build-base \
        linux-headers && \
    pip install -r ${APP_HOME}/requirements.txt && \
    apk del .build-dependencies

# chown all the files to the app user
RUN chown -R tunnel:users $APP_HOME
RUN chown -R tunnel:users /home/tunnel/ssh_socket && chown -R tunnel:users /home/tunnel/.ssh && chmod 700 /home/tunnel/.ssh

EXPOSE 22

# run entrypoint.prod.sh
ENTRYPOINT ["/home/tunnel/web/entrypoint.sh"]
