# pull official base image
FROM ubuntu:focal-20220113

RUN apt update && apt -y upgrade && DEBIAN_FRONTEND=noninteractive apt install -yq python3 python3-pip python3-django uuid-runtime openssh-server libc6 libstdc++6 ca-certificates tar bash curl wget

# create the app user
RUN adduser --uid 1000 --ingroup users --gecos "" --disabled-password tunnel

# create directory for the app user
RUN mkdir -p /home/tunnel/ssh_socket && mkdir -p /home/tunnel/.ssh

# create the appropriate directories
ENV HOME=/home/tunnel
ENV APP_HOME=/home/tunnel/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN sed -i -r \
    -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" \
    -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" \
    -e "s/^#Port 22/Port 2222/g" \ 
    /etc/ssh/sshd_config && \
    ssh-keygen -A 

RUN echo tunnel:$(uuidgen) | chpasswd

# copy project
COPY . $APP_HOME

RUN pip install -r ${APP_HOME}/requirements.txt

# chown all the files to the app user
RUN chown -R tunnel:users $APP_HOME
RUN chown -R tunnel:users /home/tunnel/ssh_socket && chown -R tunnel:users /home/tunnel/.ssh && chmod 700 /home/tunnel/.ssh

EXPOSE 22

# run entrypoint.prod.sh
ENTRYPOINT ["/home/tunnel/web/entrypoint.sh"]
