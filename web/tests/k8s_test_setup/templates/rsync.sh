#!/bin/bash

while true; do
    sleep 60
    if [[ -f <DIR>/<ID>/pids/port-forward_jupyterhub.pid ]]; then
        rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-patched <DIR>/<ID>/rsync || true
        rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/src/jupyterhub-custom <DIR>/<ID>/rsync || true
        rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/home/jupyterhub/jupyterhub_config.py <DIR>/<ID>/rsync || true
        rsync -r -c -q -b -e "ssh -p 2222 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" jupyterhub@localhost:/home/jupyterhub/jupyterhub_custom_config.json <DIR>/<ID>/rsync || true
    fi
    if [[ -f <DIR>/<ID>/pids/port-forward_backend.pid ]]; then
        rsync -r -c -q -b -e "ssh -p 2224 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" backend@localhost:/home/backend/web <DIR>/<ID>/rsync/backend || true
    fi
    if [[ -f <DIR>/<ID>/pids/port-forward_tunnel.pid ]]; then
        rsync -r -c -q -b -e "ssh -p 2223 -i <DIR>/<ID>/keypairs/devel -oLogLevel=ERROR -oUserKnownHostsFile=/dev/null -oStrictHostKeyChecking=no" tunnel@localhost:/home/tunnel/web <DIR>/<ID>/rsync/tunnel || true
    fi
done
