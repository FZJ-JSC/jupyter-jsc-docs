import os
import time
import unittest

import requests
from kubernetes import client


class FunctionalTests(unittest.TestCase):
    suffix = None
    image = None
    v1 = None
    name = None
    namespace = "gitlab"
    k8s_host = None
    k8s_user_token = None
    k8s_ca_auth_path = None

    url = None
    headers = {
        "Content-Type": "application/json",
        "Authentication": "Bearer YWRtaW46cGphZjE5MDQwMW9pYWY=",
    }

    def setUp(self):
        self.load_env()
        self.load_k8s_client()
        self.start_tunneling_pod_and_svcs()
        return super().setUp()

    def tearDown(self):
        self.delete_tunneling_pod_and_svcs()
        return super().tearDown()

    def load_env(self):
        self.suffix = os.environ.get("CI_COMMIT_SHORT_SHA", "")
        self.name = f"tunneling-devel-{self.suffix}"
        self.image = f"registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/tunneling-relaunch:{self.suffix}"
        self.k8s_host = os.environ.get("K8S_TEST_CLUSTER_SERVER", "")
        self.k8s_user_token = os.environ.get("K8S_TEST_CLUSTER_USER_TOKEN", "")
        self.k8s_ca_auth_path = os.environ.get("CA_AUTH_PATH")
        self.url = f"http://{self.name}:8080/api"

    def load_k8s_client(self):
        conf = client.Configuration()
        conf.host = self.k8s_host
        conf.api_key["authorization"] = self.k8s_user_token
        conf.api_key_prefix["authorization"] = "Bearer"
        conf.ssl_ca_cert = self.k8s_ca_auth_path
        self.v1 = client.CoreV1Api(client.ApiClient(conf))

    def get_svc_manifest(self, port, suffix=""):
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "labels": {
                    "name": f"{self.name}{suffix}",
                },
                "name": f"{self.name}{suffix}",
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
                "selector": {"name": self.name},
            },
        }

    def delete_tunneling_pod_and_svcs(self):
        self.v1.delete_namespaced_service(name=f"{self.name}", namespace=self.namespace)
        self.v1.delete_namespaced_service(
            name=f"{self.name}-ssh", namespace=self.namespace
        )
        self.v1.delete_namespaced_pod(name=self.name, namespace=self.namespace)

    def start_tunneling_pod_and_svcs(self):
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "labels": {
                    "name": self.name,
                },
                "name": self.name,
                "resourceversion": "v1",
            },
            "spec": {
                "containers": [
                    {
                        "args": ["bash"],
                        "image": self.image,
                        "imagePullPolicy": "Always",
                        "name": self.name,
                        "env": [
                            {
                                "name": "DEPLOYMENT_NAME",
                                "value": self.name,
                            },
                            {
                                "name": "DEPLOYMENT_NAMESPACE",
                                "value": self.namespace,
                            },
                            {
                                "name": "TUNNEL_SUPERUSER_PASS",
                                "value": "pjaf190401oiaf",
                            },
                        ],
                    }
                ],
                "serviceAccount": "tunneling-devel-svc-acc",
                "serviceAccountName": "tunneling-devel-svc-acc",
            },
        }
        self.v1.create_namespaced_pod(body=pod_manifest, namespace=self.namespace)
        while True:
            resp = self.v1.read_namespaced_pod(name=self.name, namespace=self.namespace)
            if resp.status.phase != "Pending":
                break
            time.sleep(1)
        self.v1.create_namespaced_service(
            body=self.get_svc_manifest(8080), namespace=self.namespace
        )
        self.v1.create_namespaced_service(
            body=self.get_svc_manifest(2222, suffix="-ssh"), namespace=self.namespace
        )

    def test_logger(self):
        r = requests.get(url=f"{self.url}/logs/logtests", headers=self.headers)
        self.assertEqual(r.status_code, 200)
