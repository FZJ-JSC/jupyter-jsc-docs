import os
import time

import requests
from kubernetes import client
from kubernetes.stream import stream


def load_env():
    suffix = os.environ.get("CI_COMMIT_SHORT_SHA", "")
    imagetag = os.environ.get("FUNCTIONAL_TEST_TAG", "")
    name = f"tunneling-devel-{suffix}"
    namespace = "gitlab"
    image = f"registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/tunneling-relaunch:{imagetag}"
    k8s_host = os.environ.get("K8S_TEST_CLUSTER_SERVER", "")
    k8s_user_token = os.environ.get("K8S_TEST_CLUSTER_USER_TOKEN", "")
    k8s_ca_auth_path = os.environ.get("CA_AUTH_PATH")
    url = f"http://{name}:8080/api"
    return (
        suffix,
        name,
        namespace,
        image,
        k8s_host,
        k8s_user_token,
        k8s_ca_auth_path,
        url,
    )


def load_k8s_client(k8s_host, k8s_user_token, k8s_ca_auth_path):
    conf = client.Configuration()
    conf.host = k8s_host
    conf.api_key["authorization"] = k8s_user_token
    conf.api_key_prefix["authorization"] = "Bearer"
    conf.ssl_ca_cert = k8s_ca_auth_path
    return client.CoreV1Api(client.ApiClient(conf))


def get_svc_manifest(name, port, suffix=""):
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "labels": {
                "name": f"{name}{suffix}",
            },
            "name": f"{name}{suffix}",
            "resourceversion": "v1",
        },
        "spec": {
            "ports": [
                {
                    "name": "port",
                    "port": port,
                    "protocol": "TCP",
                    "targetPort": port,
                }
            ],
            "selector": {"name": name},
        },
    }


def delete_tunneling_pod_and_svcs(v1, name, namespace):
    v1.delete_namespaced_service(name=name, namespace=namespace)
    v1.delete_namespaced_service(name=f"{name}-ssh", namespace=namespace)
    v1.delete_namespaced_pod(name=name, namespace=namespace)


def start_tunneling_pod_and_svcs(v1, name, namespace, image):
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "labels": {
                "name": name,
            },
            "name": name,
            "resourceversion": "v1",
        },
        "spec": {
            "containers": [
                {
                    "image": image,
                    "imagePullPolicy": "Always",
                    "name": name,
                    "env": [
                        {
                            "name": "DEPLOYMENT_NAME",
                            "value": name,
                        },
                        {
                            "name": "DEPLOYMENT_NAMESPACE",
                            "value": namespace,
                        },
                        {
                            "name": "TUNNEL_SUPERUSER_PASS",
                            "value": os.environ.get("TUNNEL_SUPERUSER_PASS"),
                        },
                        {
                            "name": "SSHCONFIGFILE",
                            "value": "/tmp/ssh_config",
                        },
                    ],
                }
            ],
            "serviceAccount": "tunneling-devel-svc-acc",
            "serviceAccountName": "tunneling-devel-svc-acc",
        },
    }
    v1.create_namespaced_pod(body=pod_manifest, namespace=namespace)
    while True:
        resp = v1.read_namespaced_pod(name=name, namespace=namespace)
        if resp.status.phase != "Pending":
            break
        time.sleep(1)
    v1.create_namespaced_service(body=get_svc_manifest(name, 8080), namespace=namespace)
    v1.create_namespaced_service(
        body=get_svc_manifest(name, 2222, suffix="-ssh"), namespace=namespace
    )


def wait_for_tunneling_svc(url):
    for _ in range(0, 40):
        try:
            r = requests.get(url=f"{url}/health/", timeout=2)
            if r.status_code == 200:
                break
        except (
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
        ):
            pass
        time.sleep(1)


def wait_for_tsi_svc(v1, name, namespace):
    exec_command = ["/bin/sh"]
    resp = stream(
        v1.connect_get_namespaced_pod_exec,
        name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=True,
        stdout=True,
        tty=False,
        _preload_content=False,
    )
    command = "netstat -ltnp 2>/dev/null | tr -s ' ' | grep \":4433\" | wc -l"
    while resp.is_open():
        for _ in range(0, 150):
            resp.write_stdin(command + "\n")
            resp.update(timeout=1)
            if resp.peek_stdout():
                stdout = resp.read_stdout().strip()
                if stdout == "1":
                    resp.close()
                    break
            time.sleep(1)
    if resp.is_open():
        resp.close()


def replace_ssh_host_in_tsi_manage_tunnel_script(
    v1, name, namespace, tunnel_ssh_svc_name
):
    exec_command = [
        "sed",
        "-i",
        "-e",
        f"s/TUNNEL_SSH_HOST=localhost/TUNNEL_SSH_HOST={tunnel_ssh_svc_name}/g",
        "/home/ljupyter/manage_tunnel.sh",
    ]
    resp = stream(
        v1.connect_get_namespaced_pod_exec,
        name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )


def add_test_files_to_tunneling(v1, name, namespace, data):
    exec_command = ["/bin/sh"]
    resp = stream(
        v1.connect_get_namespaced_pod_exec,
        name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=True,
        stdout=True,
        tty=False,
        _preload_content=False,
    )
    commands = []
    # Add authorized keys to allow unicore-test-tsi to connect to ljupyter
    commands.append("mkdir -p /home/tunnel/.ssh\n")
    commands.append("chown tunnel:users /home/tunnel/.ssh\n")
    commands.append("chmod 700 /home/tunnel/.ssh\n")
    for destination, inp, b64, chown, chmod in data:
        if b64:
            commands.append('echo -n "' + inp + '" | base64 -d >' + destination + "\n")
        else:
            commands.append('echo -n "' + inp + '\n" >' + destination + "\n")
        if chown:
            commands.append("chown " + chown + " " + destination + "\n")
        if chmod:
            commands.append("chmod " + chmod + " " + destination + "\n")
    while resp.is_open():
        resp.update(timeout=1)
        if commands:
            c = commands.pop(0)
            resp.write_stdin(c)
        else:
            break
    resp.close()


def start_unicore_tsi_pod_and_svcs(v1, name, namespace, image, tunnel_ssh_svc):
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "labels": {
                "name": name,
            },
            "name": name,
            "resourceversion": "v1",
        },
        "spec": {
            "containers": [
                {
                    "image": image,
                    "imagePullPolicy": "Always",
                    "name": name,
                    "env": [
                        {
                            "name": "TUNNEL_SSH_HOST",
                            "value": tunnel_ssh_svc,
                        },
                    ],
                }
            ],
            "imagePullSecrets": [{"name": "gitlab-registry"}],
        },
    }
    v1.create_namespaced_pod(body=pod_manifest, namespace=namespace)
    while True:
        resp = v1.read_namespaced_pod(name=name, namespace=namespace)
        if resp.status.phase != "Pending":
            break
        time.sleep(1)
    v1.create_namespaced_service(
        body=get_svc_manifest(name, 2223, suffix="-ssh"), namespace=namespace
    )


def delete_unicore_tsi_pod_and_svcs(v1, name, namespace):
    v1.delete_namespaced_service(name=f"{name}-ssh", namespace=namespace)
    v1.delete_namespaced_pod(name=name, namespace=namespace)
