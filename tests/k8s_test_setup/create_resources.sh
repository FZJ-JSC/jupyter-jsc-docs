#!/bin/bash
DEVEL_TUNNEL="false"

UNITY_VERSION="3.8.1-k8s-1"
UNICORE_VERSION="8.3.0-5"
TUNNEL_VERSION="1.0.0-26"


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BASE_TESTS=$(dirname $DIR)
BASE=$(dirname $BASE_TESTS)

ID_LONG=$(uuidgen | tr 'A-Z' 'a-z')
ID=${ID_LONG:0:8}
NEW_DIR="tests"
NAMESPACE="gitlab"
echo "Create yaml files and JupyterHub configurations for unique identifier: ${ID}"

# Create Certs
mkdir -p ${DIR}/${NEW_DIR}/certs
cp ${DIR}/templates/certs/ca-root.pem ${DIR}/${NEW_DIR}/certs/.
create_certificate () {
    SERVICE=${1}
    CN=${2}
    ALT_NAME=${3}
    KEYSTORE_PASS=${4}
    KEYSTORE_NAME=${5}
    sed -e "s!<CN>!${CN}!g" -e "s!<ALT_NAME>!${ALT_NAME}!g" ${DIR}/templates/certs/template.cnf > ${DIR}/${NEW_DIR}/certs/${SERVICE}.cnf
    openssl genrsa -out ${DIR}/${NEW_DIR}/certs/${SERVICE}.key 2048 &> /dev/null
    openssl req -new -key ${DIR}/${NEW_DIR}/certs/${SERVICE}.key -out ${DIR}/${NEW_DIR}/certs/${SERVICE}.csr -config  ${DIR}/${NEW_DIR}/certs/${SERVICE}.cnf
    openssl x509 -req -in ${DIR}/${NEW_DIR}/certs/${SERVICE}.csr -CA ${DIR}/templates/certs/ca-root.pem -CAkey ${DIR}/templates/certs/ca.key -CAcreateserial -out ${DIR}/${NEW_DIR}/certs/${SERVICE}.crt -days 365 -sha512 -extfile ${DIR}/${NEW_DIR}/certs/${SERVICE}.cnf -extensions v3_req &> /dev/null
    # Create keystores with pass
    if [[ ${KEYSTORE_NAME} == "" ]]; then
        openssl pkcs12 -export -in ${DIR}/${NEW_DIR}/certs/${SERVICE}.crt -inkey ${DIR}/${NEW_DIR}/certs/${SERVICE}.key -certfile ${DIR}/templates/certs/ca-root.pem -out ${DIR}/${NEW_DIR}/certs/${SERVICE}.p12 -password pass:${KEYSTORE_PASS};
    else
        openssl pkcs12 -export -name ${KEYSTORE_NAME} -in ${DIR}/${NEW_DIR}/certs/${SERVICE}.crt -inkey ${DIR}/${NEW_DIR}/certs/${SERVICE}.key -certfile ${DIR}/templates/certs/ca-root.pem -out ${DIR}/${NEW_DIR}/certs/${SERVICE}.p12 -password pass:${KEYSTORE_PASS};
    fi
}
create_certificate "gateway" "unicore-gateway" "unicore-${ID}.${NAMESPACE}.svc" 'the!gateway'
create_certificate "unicorex" "unicore-unicorex" "unicore-${ID}.${NAMESPACE}.svc" 'the!njs'
create_certificate "tsi" "unicore-tsi" "unicore-${ID}.${NAMESPACE}.svc" 'the!tsi'
create_certificate "unity" "unity" "unity-${ID}.${NAMESPACE}.svc" 'the!unity' "unity-test-server"
create_certificate "tunnel" "tunnel" "tunnel-${ID}.${NAMESPACE}.svc" 'the!tunnel' 

# Create KeyPairs
mkdir -p ${DIR}/${NEW_DIR}/keypairs
create_keypair () {
    ssh-keygen -f ${DIR}/${NEW_DIR}/keypairs/${1} -t ed25519 -q -N ""
}
create_keypair "ljupyter"
create_keypair "tunnel"
create_keypair "remote"
create_keypair "reservation"
create_keypair "devel"


# Prepare input files for each services
JUPYTERHUB_ALT_NAME="jupyterhub-${ID}.${NAMESPACE}.svc"
TUNNEL_ALT_NAME="tunnel-${ID}.${NAMESPACE}.svc"
BACKEND_ALT_NAME="backend-${ID}.${NAMESPACE}.svc"
UNICORE_ALT_NAME="unicore-${ID}.${NAMESPACE}.svc"
UNITY_ALT_NAME="unity-${ID}.${NAMESPACE}.svc"
TUNNEL_PUBLIC_KEY=$(cat ${DIR}/${NEW_DIR}/keypairs/tunnel.pub)
ESCAPED_TPK=$(printf '%s\n' "$TUNNEL_PUBLIC_KEY" | sed -e 's/[\!&]/\\&/g')
REMOTE_PUBLIC_KEY="$(cat ${DIR}/${NEW_DIR}/keypairs/remote.pub)"
ESCAPED_RPK=$(printf '%s\n' "$REMOTE_PUBLIC_KEY" | sed -e 's/[\!&]/\\&/g')
LJUPYTER_PUBLIC_KEY="$(cat ${DIR}/${NEW_DIR}/keypairs/ljupyter.pub)"
ESCAPED_LPK=$(printf '%s\n' "$LJUPYTER_PUBLIC_KEY" | sed -e 's/[\!&]/\\&/g')
DEVEL_PUBLIC_KEY="$(cat ${DIR}/${NEW_DIR}/keypairs/devel.pub)"
ESCAPED_DPK=$(printf '%s\n' "$DEVEL_PUBLIC_KEY" | sed -e 's/[\!&]/\\&/g')
UNICORE_SSH_PORT="22"

JUPYTERHUB_PORT="30800"

cp -rp ${DIR}/templates/files ${DIR}/${NEW_DIR}/.
find ${DIR}/${NEW_DIR}/files -type f -exec sed -i '' -e "s!<DIR>!${DIR}!g" -e "s!<BACKEND_JHUB_BASIC>!${BACKEND_JHUB_BASIC}!g" -e "s!<NAMESPACE>!${NAMESPACE}!g" -e "s!<ID>!${ID}!g" -e "s!<UNITY_ALT_NAME>!${UNITY_ALT_NAME}!g" -e "s!<UNICORE_ALT_NAME>!${UNICORE_ALT_NAME}!g" -e "s!<TUNNEL_ALT_NAME>!${TUNNEL_ALT_NAME}!g" -e "s!<JUPYTERHUB_ALT_NAME>!${JUPYTERHUB_ALT_NAME}!g" -e "s!<JUPYTERHUB_PORT>!${JUPYTERHUB_PORT}!g" -e "s!<TUNNEL_PUBLIC_KEY>!${ESCAPED_TPK}!g" -e "s!<REMOTE_PUBLIC_KEY>!${ESCAPED_RPK}!g" -e "s!<LJUPYTER_PUBLIC_KEY>!${ESCAPED_LPK}!g" -e "s!<DEVEL_PUBLIC_KEY>!${ESCAPED_DPK}!g" -e "s!<UNICORE_SSH_PORT>!${UNICORE_SSH_PORT}!g" {} \; 2> /dev/null
tar -czf ${DIR}/${NEW_DIR}/files/backend/job_descriptions.tar.gz -C ${DIR}/${NEW_DIR}/files/backend/ job_descriptions

# Create passwords / secrets for Django services
BACKEND_SECRET=$(uuidgen)
TUNNEL_SECRET=$(uuidgen)
TUNNEL_SUPERUSER_PASS=$(uuidgen)
TUNNEL_BACKEND_PASS=$(uuidgen)
TUNNEL_JHUB_PASS=$(uuidgen)
BACKEND_SUPERUSER_PASS=$(uuidgen)
BACKEND_JHUB_PASS=$(uuidgen)

get_basic_token () {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TMP=$(echo -n "${1}:${2}" | base64)
    else
        TMP=$(echo -n "${1}:${2}" | base64 -w 0)
    fi
    echo "Basic ${TMP}"
}
TUNNEL_BACKEND_BASIC=$(get_basic_token "backend" ${TUNNEL_BACKEND_PASS})
TUNNEL_JHUB_BASIC=$(get_basic_token "jupyterhub" ${TUNNEL_JHUB_PASS})
BACKEND_JHUB_BASIC=$(get_basic_token "jupyterhub" ${BACKEND_JHUB_PASS})


# Prepare yaml files
cp -rp ${DIR}/templates/yaml ${DIR}/${NEW_DIR}/.

select_yaml_file () {
    if [[ ${1} == "true" ]]; then
        mv ${DIR}/${NEW_DIR}/yaml/${2}_devel.yaml ${DIR}/${NEW_DIR}/yaml/${2}.yaml
    else
        rm ${DIR}/${NEW_DIR}/yaml/${2}_devel.yaml
    fi
}
select_yaml_file ${DEVEL_TUNNEL} "tunnel"

if [[ -n $CI_PROJECT_DIR ]]; then
    rm ${DIR}/${NEW_DIR}/yaml/ingress*
fi

find ${DIR}/${NEW_DIR}/yaml -type f -exec sed -i '' -e "s!<JUPYTERHUB_ALT_NAME>!${JUPYTERHUB_ALT_NAME}!g" -e "s!<JUPYTERHUB_VERSION>!${JUPYTERHUB_VERSION}!g" -e "s!<UNITY_VERSION>!${UNITY_VERSION}!g" -e "s!<UNICORE_VERSION>!${UNICORE_VERSION}!g" -e "s!<TUNNEL_VERSION>!${TUNNEL_VERSION}!g" -e "s!<JUPYTERHUB_PORT>!${JUPYTERHUB_PORT}!g" -e "s!<BACKEND_VERSION>!${BACKEND_VERSION}!g" -e "s!<_VERSION>!${_VERSION}!g" -e "s!<DIR>!${DIR}!g" -e "s!<BACKEND_JHUB_BASIC>!${BACKEND_JHUB_BASIC}!g" -e "s!<ID>!${ID}!g" -e "s!<NAMESPACE>!${NAMESPACE}!g" {} \; 2> /dev/null
kubectl -n ${NAMESPACE} create configmap --dry-run=client unicore-files-${ID} --from-file=${DIR}/${NEW_DIR}/files/unicore --output yaml > ${DIR}/${NEW_DIR}/yaml/cm-unicore-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client backend-files-${ID} --from-file=${DIR}/${NEW_DIR}/files/backend --output yaml > ${DIR}/${NEW_DIR}/yaml/cm-backend-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client tunnel-files-${ID} --from-file=${DIR}/${NEW_DIR}/files/tunnel --output yaml > ${DIR}/${NEW_DIR}/yaml/cm-tunnel-files.yaml
kubectl -n ${NAMESPACE} create configmap --dry-run=client jupyterhub-files-${ID} --from-file=${DIR}/${NEW_DIR}/files/jupyterhub --output yaml > ${DIR}/${NEW_DIR}/yaml/cm-jupyterhub-files.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client backend-drf-${ID} --from-literal=backend_secret=${BACKEND_SECRET} --from-literal=superuser_pass=${BACKEND_SUPERUSER_PASS} --from-literal=jupyterhub_pass=${BACKEND_JHUB_PASS} --from-literal=jupyterhub_basic="${BACKEND_JHUB_BASIC}" --output yaml > ${DIR}/${NEW_DIR}/yaml/secret-backend-drf.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client tunnel-drf-${ID} --from-literal=tunnel_secret=${TUNNEL_SECRET} --from-literal=superuser_pass=${TUNNEL_SUPERUSER_PASS} --from-literal=backend_pass=${TUNNEL_BACKEND_PASS} --from-literal=backend_basic="${TUNNEL_BACKEND_BASIC}" --from-literal=jupyterhub_pass=${TUNNEL_JHUB_PASS} --from-literal=jupyterhub_basic="${TUNNEL_JHUB_BASIC}" --output yaml > ${DIR}/${NEW_DIR}/yaml/secret-tunnel-drf.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client --output yaml --from-file=${DIR}/${NEW_DIR}/keypairs keypairs-${ID} > ${DIR}/${NEW_DIR}/yaml/secret-keypairs.yaml
kubectl -n ${NAMESPACE} create secret generic --dry-run=client --output yaml --from-file=${DIR}/${NEW_DIR}/certs certs-${ID} > ${DIR}/${NEW_DIR}/yaml/secret-certs.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${NEW_DIR}/certs/unity.crt --key=${DIR}/${NEW_DIR}/certs/unity.key tls-unity-${ID} > ${DIR}/${NEW_DIR}/yaml/tls-unity.yaml
kubectl -n ${NAMESPACE} create secret tls --dry-run=client --output yaml --cert=${DIR}/${NEW_DIR}/certs/gateway.crt --key=${DIR}/${NEW_DIR}/certs/gateway.key tls-gateway-${ID} > ${DIR}/${NEW_DIR}/yaml/tls-gateway.yaml

kubectl -n ${NAMESPACE} apply -f ${DIR}/${NEW_DIR}/yaml

if [[ -z $CI_PROJECT_DIR ]]; then
    echo "Waiting for ingress to setup address ..."
    COUNTER=30
    IP=$(kubectl -n ${NAMESPACE} get ingress ingress-http-${ID} --output=jsonpath={.status.loadBalancer.ingress[0].ip})
    while [[ ${IP} == "" ]]; do
        let COUNTER-=1
        sleep 4
        IP=$(kubectl -n ${NAMESPACE} get ingress ingress-http-${ID} --output=jsonpath={.status.loadBalancer.ingress[0].ip})
    done

    if [[ $COUNTER -eq 0 ]]; then
        echo "Received no external IP address for ingress resource ingress-http-${ID}"
        kubectl -n ${NAMESPACE} get ingress ingress-http-${ID}
        exit 1
    fi
    echo "${IP} tunnel-${ID}.${NAMESPACE}.svc unity-${ID}.${NAMESPACE}.svc unicore-${ID}.${NAMESPACE}.svc"
    read -p "Add the line above to /etc/hosts and press Enter to continue: "

fi


wait_for_service () {
    echo "Wait for ${1} ..."
    COUNTER=30
    STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" ${1})
    while [[ ! $STATUS_CODE -eq 200 ]]; do
        let COUNTER-=1
        sleep 2
        STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "GET" ${1})
    done
    if [[ $COUNTER -eq 0 ]]; then
        echo "${1} not reachable after 60 seconds. Exit"
        exit 1
    fi
}

wait_for_service "https://${UNICORE_ALT_NAME}/"

wait_for_drf_service () {
    if [[ ! ${3} == "true" ]]; then
        wait_for_service ${1}/api/health/
        STATUS_CODE=$(curl --write-out '%{http_code}' --silent --output /dev/null -X "POST" -H "Content-Type: application/json" -H "Authorization: ${2}" -d '{"handler": "stream", "configuration": {"formatter": "simple", "level": 5, "stream": "ext://sys.stdout"}}' ${1}/api/logs/handler/)
        if [[ ! $STATUS_CODE -eq 201 ]]; then
            echo "Could not add stream handler to ${1}. Status Code: $STATUS_CODE"
        fi
    fi
}
wait_for_drf_service "http://${TUNNEL_ALT_NAME}" "${TUNNEL_JHUB_BASIC}" ${DEVEL_TUNNEL}

UNICORE_POD_NAME=$(kubectl -n ${NAMESPACE} get pod -l app=unicore-${ID} -o jsonpath="{.items[0].metadata.name}")
TUNNEL_POD_NAME=$(kubectl -n ${NAMESPACE} get pod -l app=tunnel-${ID} -o jsonpath="{.items[0].metadata.name}")

sed -i -e "s!<KUBECONFIG>!${DIR}/kube_config!g" -e "s!<NAMESPACE>!${NAMESPACE}!g" -e "s!<TUNNEL_URL>!${TUNNEL_ALT_NAME}!g" -e "s!<TUNNEL_POD>!${TUNNEL_POD_NAME}!g" -e "s!<UNICORE_URL>!${UNICORE_ALT_NAME}!g" -e "s!<UNICORE_POD>!${UNICORE_POD_NAME}!g" -e "s!<TUNNEL_JHUB_BASIC>!${TUNNEL_JHUB_BASIC}!g" ${DIR}/${NEW_DIR}/files/pytest.ini

echo "Used pytest.ini file: "
cat ${DIR}/${NEW_DIR}/files/pytest.ini
