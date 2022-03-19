#!/bin/bash

if [[ -z ${1} ]]; then
    echo "Argument (name of patch) required. Will be used in patch file name: <name>.patch"
    exit 1
fi

cd /src/jupyterhub && diff -Naurx .git -x node_modules -x share -x __pycache__ ../jupyterhub/jupyterhub ../jupyterhub-patched/jupyterhub > /home/jupyterhub/${1}.patch
