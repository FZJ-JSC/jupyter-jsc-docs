#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
NEW_DIR="tests"

kubectl delete -f ${DIR}/${NEW_DIR}/yaml 2> /dev/null
stop_port_forward_svc () {
    if [[ -f ${DIR}/${NEW_DIR}/pids/port-forward_${1}.pid ]]; then
        kill -9 $(cat ${DIR}/${NEW_DIR}/pids/port-forward_${1}.pid)
    fi
}
stop_port_forward_svc "jupyterhub"
stop_port_forward_svc "tunnel"
stop_port_forward_svc "backend"
if [[ -f ${DIR}/${NEW_DIR}/pids/rsync.pid ]]; then
    kill -9 $(cat ${DIR}/${NEW_DIR}/pids/rsync.pid)
fi

rm -r ${DIR}/${NEW_DIR}/certs
rm -r ${DIR}/${NEW_DIR}/files
rm -r ${DIR}/${NEW_DIR}/keypairs
rm -r ${DIR}/${NEW_DIR}/pids
rm -r ${DIR}/${NEW_DIR}/yaml

echo "-----------------"
echo "rsync folder not deleted. To do so: "
echo "rm -r ${DIR}/${NEW_DIR}"
