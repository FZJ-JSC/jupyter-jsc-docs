#!/bin/bash
_term() {
  echo "Caught SIGTERM signal!"
  kill -TERM "$child" 2>/dev/null
}
trap _term SIGTERM

echo "Hello World from my Script"

# Give UNICORE time to create files correctly
sleep 2
# Get current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export JUPYTERHUB_API_TOKEN=$(cat ${DIR}/.jupyter.token)
export JUPYTERHUB_OAUTH_SCOPES=$(cat ${DIR}/.oauth.scopes)

env &> env_output

export JUPYTER_JSC_HOME=${HOME}

sed -i -e "s|_port_|${PORT}|g" -e "s|_home_|${JUPYTER_JSC_HOME}|g" -e "s|_servername_|${JUPYTERHUB_SERVER_NAME}|g" -e "s|_username_|${JUPYTERHUB_USER}|g" -e "s|_remotenode_|${JUPYTER_JSC_REMOTENODE}|g" -e "s|_remoteport_|${JUPYTER_JSC_REMOTEPORT}|g" ${DIR}/config.py

sleep 1
# curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 25, "failed": false, "html_message": "Msg 25"}' -X "POST" http://jupyterhub.gitlab.svc:8000/hub/api/users/progress/update/demo-user-1@example.com
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 25, "failed": false, "html_message": "Msg 25"}' -X "POST" http://jupyterhub-6515fb85.gitlab.svc/hub/api/${JUPYTERHUB_STATUS_URL}
sleep 1
# curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 50, "failed": false, "html_message": "Msg 50"}' -X "POST" http://jupyterhub.gitlab.svc:8000/hub/api/users/progress/update/demo-user-1@example.com
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 50, "failed": false, "html_message": "Msg 50"}' -X "POST" http://jupyterhub-6515fb85.gitlab.svc/hub/api/${JUPYTERHUB_STATUS_URL}
sleep 1
# curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 75, "failed": false, "html_message": "Msg 75"}' -X "POST" http://jupyterhub.gitlab.svc:8000/hub/api/users/progress/update/demo-user-1@example.com
curl -H "Authorization: token ${JUPYTERHUB_API_TOKEN}" -H "Content-Type: application/json" -d '{"progress": 75, "failed": false, "html_message": "Msg 75"}' -X "POST" http://jupyterhub-6515fb85.gitlab.svc/hub/api/${JUPYTERHUB_STATUS_URL}

timeout 3d jupyterhub-singleuser --debug --config ${DIR}/config.py &
child=$!
wait $child
