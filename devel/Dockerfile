FROM ubuntu:focal-20240530

ENV DEBIAN_FRONTEND noninteractive

ENV USERNAME=tunnel

# create the app user
RUN adduser --uid 1000 --ingroup users --gecos "" --disabled-password ${USERNAME}

# create the appropriate directories
ENV HOME=/home/${USERNAME}
ENV APP_HOME=/home/${USERNAME}/web
RUN mkdir -p ${APP_HOME} && \
    mkdir -p ${HOME}/certs && \
    mkdir -p ${HOME}/services/services && \
    mkdir -p ${HOME}/services/job_descriptions && \
    mkdir -p ${HOME}/userhomes && \
    mkdir -p ${APP_HOME}/.vscode && \
    mkdir -p ${HOME}/.ssh
WORKDIR ${APP_HOME}

RUN apt update && \
    apt -y upgrade && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* 
    
# Install app requirements
COPY ./devel/requirements_build.txt /tmp/requirements_pip.txt
COPY devel/requirements_apt.txt /tmp/requirements_apt.txt
RUN apt update && \
    cat /tmp/requirements_apt.txt | xargs apt install -yq && \
    apt clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -r /tmp/requirements_pip.txt && \
    chown -R ${USERNAME}:users ${HOME} && \
    rm /tmp/requirements_pip.txt && \
    rm /tmp/requirements_apt.txt && \
    sed -i -r \
    -e "s/^#PasswordAuthentication yes/PasswordAuthentication no/g" \
    -e "s/^AllowTcpForwarding no/AllowTcpForwarding yes/g" \
    -e "s/^#Port 22/Port 2222/g" \
    /etc/ssh/sshd_config && \
    mkdir -p /run/sshd && \
    ssh-keygen -A

RUN echo ${USERNAME}:$(uuidgen) | chpasswd

# copy project
COPY web ${APP_HOME}

# Add devel entrypoint
COPY devel/entrypoint.sh ${APP_HOME}/entrypoint.sh

# chown all the files to the app user
RUN chown -R ${USERNAME}:users ${APP_HOME}

ENTRYPOINT ["/home/tunnel/web/entrypoint.sh"]
