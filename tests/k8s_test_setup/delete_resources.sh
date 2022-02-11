#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
NEW_DIR="tests"

kubectl delete -f ${DIR}/${NEW_DIR}/yaml 2> /dev/null

rm -r ${DIR}/${NEW_DIR}
