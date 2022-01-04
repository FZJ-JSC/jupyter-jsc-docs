import copy
import json
import os
import time
import unittest

import pytest
import requests
from kubernetes import client
from kubernetes.stream import stream
from parameterized import parameterized


def load_env():
    suffix = os.environ.get("CI_COMMIT_SHORT_SHA", "")
    name = f"tunneling-devel-{suffix}"
    namespace = "gitlab"
    image = (
        f"registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/tunneling-relaunch:{suffix}"
    )
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
                            "value": "/home/tunnel/web/tests/config/functional_tests/ssh_config",
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
        for _ in range(0, 15):
            resp.update(timeout=1)
            if resp.peek_stdout():
                stdout = resp.read_stdout()
                print("STDOUT: %s" % stdout)
                if stdout == "1":
                    break
            if resp.peek_stderr():
                print("STDERR: %s" % resp.read_stderr())
            print("UNICORE TSI not running yet")
            print("Running command... %s\n" % command)
            resp.write_stdin(command + "\n")
            time.sleep(10)
    resp.close()

    # ; sleep 10; let COUNTER-=1; fi; done; if [[ $COUNTER -eq 0 ]]; then echo "TSI GateWay not reachable. Exit"; exit 1; fi


def start_unicore_tsi_pod_and_svcs(v1, name, namespace, image):
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
    v1.create_namespaced_service(body=get_svc_manifest(name, 2223), namespace=namespace)


def delete_unicore_tsi_pod_and_svcs(v1, name, namespace):
    v1.delete_namespaced_service(name=name, namespace=namespace)
    v1.delete_namespaced_pod(name=name, namespace=namespace)


class FunctionalTests(unittest.TestCase):
    suffix = None
    image = None
    v1 = None
    name = None
    namespace = None
    k8s_host = None
    k8s_user_token = None
    k8s_ca_auth_path = None

    v1 = None
    url = None
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic YWRtaW46cGphZjE5MDQwMW9pYWY=",
    }

    def setUp(self):
        (
            self.suffix,
            self.name,
            self.namespace,
            self.image,
            self.k8s_host,
            self.k8s_user_token,
            self.k8s_ca_auth_path,
            self.url,
        ) = load_env()
        self.v1 = load_k8s_client(
            self.k8s_host, self.k8s_user_token, self.k8s_ca_auth_path
        )
        return super().setUp()

    @classmethod
    def setUpClass(cls):
        (
            suffix,
            name,
            namespace,
            image,
            k8s_host,
            k8s_user_token,
            k8s_ca_auth_path,
            url,
        ) = load_env()
        v1 = load_k8s_client(k8s_host, k8s_user_token, k8s_ca_auth_path)
        start_tunneling_pod_and_svcs(v1, name, namespace, image)
        tsi_version = os.environ.get("UNICORE_TSI_VERSION")
        tsi_image = f"registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/unicore-test-server/unicore-tsi-slurm:{tsi_version}"
        tsi_name = "unicore-test-tsi"
        start_unicore_tsi_pod_and_svcs(v1, tsi_name, namespace, tsi_image)
        time.sleep(15)
        wait_for_tunneling_svc(url)

    @classmethod
    def tearDownClass(cls):
        (
            suffix,
            name,
            namespace,
            image,
            k8s_host,
            k8s_user_token,
            k8s_ca_auth_path,
            url,
        ) = load_env()
        v1 = load_k8s_client(k8s_host, k8s_user_token, k8s_ca_auth_path)
        # delete_tunneling_pod_and_svcs(v1, name, namespace)
        tsi_name = "unicore-test-tsi"
        # delete_unicore_tsi_pod_and_svcs(v1, tsi_name, namespace)

    def logtest_stream(self):
        logtest_url = f"{self.url}/logs/logtest/"
        logs_1 = (
            self.v1.read_namespaced_pod_log(name=self.name, namespace=self.namespace)
            .strip()
            .split("\n")
        )
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.url)
        logs_2 = (
            self.v1.read_namespaced_pod_log(name=self.name, namespace=self.namespace)
            .strip()
            .split("\n")
        )
        return logs_1, logs_2

    def test_health(self):
        r = requests.get(url=f"{self.url}/health/", headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.url)

    configurations = {
        "stream": {
            "handler": "stream",
            "configuration": {
                "formatter": "simple",
                "level": 10,
                "stream": "ext://sys.stdout",
            },
        },
        "file": {
            "handler": "file",
            "configuration": {
                "formatter": "json",
                "level": 10,
                "stream": "ext://sys.stdout",
            },
        },
    }

    @parameterized.expand(
        [
            ("stream", "simple"),
            ("stream", "json"),
        ]
    )
    def no_test_stream_handler(self, handler, formatter):
        handler_url = f"{self.url}/logs/handler/"
        stream_url = f"{self.url}/logs/handler/stream/"
        body = copy.deepcopy(self.configurations[handler])
        body["configuration"]["formatter"] = formatter

        # Check that nothing's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

        # Test stdout with no handler defined
        logs_1, logs_2 = self.logtest()
        self.assertEqual(len(logs_1) + 4, len(logs_2))
        self.assertEqual(logs_2[-4:-1], ["Warn", "Error", "Critical"])

        # Add Stream handler
        r = requests.post(url=handler_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 201)

        # Check that something's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])
        r = requests.get(url=stream_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), {})

        # Test Stream handler
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 6, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-6].endswith("function=list : Debug"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-6])["Message"], "Debug")

        # Test mix_extra in formatter
        if formatter == "simple":
            self.assertTrue(
                logs_2[-2].endswith(
                    "function=list : Critical --- Extra1=message1 --- mesg=msg1"
                )
            )
        elif formatter == "json":
            tmp = json.loads(logs_2[-2])
            self.assertEqual(tmp["Message"], "Critical")
            self.assertEqual(tmp["Extra1"], "message1")
            self.assertEqual(tmp["mesg"], "msg1")

        # Update Stream handler Loglevel with POST
        body["configuration"]["level"] = 5
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with TRACE
        logs_1, logs_2 = self.logtest()
        self.assertEqual(len(logs_1) + 7, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-7].endswith("function=list : Trace"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-7])["Message"], "Trace")

        # Update LogLevel to DEACTIVATE
        body["configuration"]["level"] = "DEACTIVATE"
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with DEACTIVATE
        logs_1, logs_2 = self.logtest()
        self.assertEqual(len(logs_1) + 1, len(logs_2))

        # Delete handler
        r = requests.delete(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 204)

        # Test stdout with no handler defined
        logs_1, logs_2 = self.logtest()
        self.assertEqual(len(logs_1) + 4, len(logs_2))
        self.assertEqual(logs_2[-4:-1], ["Warn", "Error", "Critical"])
